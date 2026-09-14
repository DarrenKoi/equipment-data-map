"""Spike regressions with fake transport responses; no server or equipment needed."""

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace as NS
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import spike
from ftp_handler.direct_downloader.fleet_downloader import (
    DownloadReport, FileResult, FileSize, HostFailure, HostListing,
    ListingReport, SizingReport,
)


class FakeTransport:
    def __init__(self, tree, payloads=None, sizes=None):
        self.tree = tree
        self.payloads = payloads or {}
        self.sizes = sizes or {}
        self.calls = []

    def list_dirs(self, specs):
        listings = []
        for spec in specs:
            for listing in spec.listings:
                self.calls.append(("list", listing.remote_dir))
                listings.append(HostListing(spec.host, self.tree.get(listing.remote_dir, [])))
        return ListingReport(listings, [])

    def size_dirs(self, specs):
        files, failures = [], []
        for spec in specs:
            paths = list(spec.files)
            for listing in spec.listings:
                paths.extend(self.tree.get(listing.remote_dir, []))
            for path in paths:
                self.calls.append(("size", path))
                if path in self.tree:
                    failures.append(HostFailure(spec.host, "error_perm: directory", path))
                else:
                    files.append(FileSize(spec.host, path, self.sizes.get(path, 1)))
        return SizingReport(files, failures)

    def download(self, specs):
        files, failures = [], []
        for spec in specs:
            for path in spec.files:
                self.calls.append(("download", path))
                data = self.payloads.get(path, b"sample")
                if isinstance(data, Exception):
                    failures.append(HostFailure(spec.host, "OSError: fake", path))
                else:
                    files.append(FileResult(spec.host, path, data))
        return DownloadReport(files, failures)


class SpikeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def run_spike(self, transport, roots=None, deny=None, budget=100, response=None):
        config = self.root / "fake.toml"
        config.write_text(
            '[equipment]\nname="fake"\nhost="fake"\nuser="ro"\npassword="ro-secret"\n'
            f'roots={json.dumps(roots if roots is not None else ["/log"])}\n'
            f'deny={json.dumps(deny or [])}\n'
            f'[budget]\nmax_dirs=10\nmax_download_bytes={budget}\nsample_bytes=8\n'
            '[llm]\nurl="http://fake"\nmodel="fake"\napi_key="llm-secret"\n'
            f'[output]\ndir={json.dumps(str(self.root / "out"))}\n', encoding="utf-8",
        )
        if response is None:
            response = {"model": "fake", "choices": [{"message": {
                "content": "### Observed\nA file."}}]}
        reply = NS(status_code=200, raise_for_status=lambda: None, json=lambda: response)
        with patch.object(spike, "fleet_downloader", return_value=lambda **kw: transport), \
                patch.object(spike.requests, "post", return_value=reply,
                             side_effect=response if isinstance(response, Exception) else None), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = spike.main(config)
        return code, json.loads(stdout.getvalue())

    def test_untrusted_listing_paths_never_reach_size_or_download(self):
        transport = FakeTransport({"/log": [
            "/log/good.log", "/other/leak.csv", "/log/../outside.txt", "/logs/x.ini",
            "/log/private.bak", "/log/tmp", "/log/tmp/hidden.txt",
        ], "/log/tmp": ["/log/tmp/hidden.txt"]})
        self.run_spike(transport, deny=["*.bak", "tmp", "tmp/*"])
        self.assertEqual(transport.calls, [
            ("list", "/log"), ("size", "/log/good.log"), ("download", "/log/good.log"),
        ])

    def test_site_noise_never_reaches_the_wire_without_deny_config(self):
        kept = ["/log/temperature.log", "/log/template.xml", "/log/attempt.log",
                "/log/tmpfile.txt", "/log/lockfile.cfg"]
        noise = ["/log/old.BAK", "/log/disk.iso", "/log/run.lock", "/log/temp.txt",
                 "/log/log_tmp_1.csv", "/log/TEMP-001.dat", "/log/~tmp", "/log/backup.tmp",
                 "/log/Temp", "/log/Temp/inside.log"]
        transport = FakeTransport({"/log": kept + noise, "/log/Temp": ["/log/Temp/inside.log"]})
        self.run_spike(transport)
        touched = {path for _, path in transport.calls}
        self.assertLessEqual(set(kept), touched)
        self.assertEqual(set(noise) & touched, set())

    def test_root_slash_discovers_children(self):
        transport = FakeTransport({"/": ["/log"], "/log": ["/log/a.txt"]})
        self.run_spike(transport, roots=["/"])
        self.assertIn(("list", "/log"), transport.calls)
        self.assertIn(("download", "/log/a.txt"), transport.calls)

    def test_denied_configured_root_is_not_listed(self):
        transport = FakeTransport({"/private": ["/private/a.txt"]})
        self.run_spike(transport, roots=["/private"], deny=["private"])
        self.assertEqual(transport.calls, [])

    def test_normalized_root_aliases_are_visited_once(self):
        transport = FakeTransport({"/log": ["/log/a.txt"]})
        code, stats = self.run_spike(transport, roots=["/log", "/log/", "/x/../log"])
        self.assertEqual(code, 0)
        self.assertEqual(stats["dirs"], 1)
        self.assertEqual(transport.calls.count(("download", "/log/a.txt")), 1)

    def test_growing_file_counts_actual_bytes_and_stops_next_transfer(self):
        transport = FakeTransport({"/log": ["/log/a.csv", "/log/b.txt"]},
                                  payloads={"/log/a.csv": b"x" * 20})
        _, stats = self.run_spike(transport, budget=10)
        self.assertEqual(stats["bytes"], 20)
        self.assertEqual(stats["overrun_bytes"], 10)
        self.assertEqual(stats["estimated_bytes"], 1)
        self.assertNotIn(("download", "/log/b.txt"), transport.calls)

    def test_estimated_size_does_not_block_first_whole_file(self):
        transport = FakeTransport({"/log": ["/log/a.txt"]},
                                  payloads={"/log/a.txt": b"x" * 20}, sizes={"/log/a.txt": 20})
        _, stats = self.run_spike(transport, budget=10)
        self.assertIn(("download", "/log/a.txt"), transport.calls)
        self.assertEqual(stats["bytes"], 20)

    def test_failed_transfer_stops_new_downloads_with_unknown_usage(self):
        transport = FakeTransport({"/log": ["/log/a.csv", "/log/b.txt"]},
                                  payloads={"/log/a.csv": OSError("fake")})
        code, stats = self.run_spike(transport)
        self.assertEqual(stats["bytes"], 0)
        self.assertNotEqual(code, 0)
        self.assertEqual(stats["download_failed"], 1)
        self.assertTrue(stats["usage_unknown"])
        self.assertNotIn(("download", "/log/b.txt"), transport.calls)

    def test_zero_budget_sends_no_download(self):
        transport = FakeTransport({"/log": ["/log/a.txt"]})
        self.run_spike(transport, budget=0)
        self.assertNotIn(("download", "/log/a.txt"), transport.calls)

    def test_llm_failure_cannot_pass(self):
        transport = FakeTransport({"/log": ["/log/a.txt"]})
        code, stats = self.run_spike(transport, response=RuntimeError("ro-secret llm-secret"))
        self.assertNotEqual(code, 0)
        self.assertEqual(stats["llm_success"], 0)
        self.assertEqual(stats["llm_failed"], 1)

    def test_invalid_llm_content_cannot_pass(self):
        for content in (None, "", "Unstructured answer", "### Observed\n",
                        "### Observed\nA file.\n### Inferred\nProbably logs."):
            with self.subTest(content=content):
                code, _ = self.run_spike(FakeTransport({"/log": ["/log/a.txt"]}), response={
                    "choices": [{"message": {"content": content}}]})
                self.assertNotEqual(code, 0)

    def test_empty_inventory_cannot_pass(self):
        code, _ = self.run_spike(FakeTransport({"/log": []}))
        self.assertNotEqual(code, 0)

    def test_directory_names_do_not_overwrite_each_other_or_index(self):
        transport = FakeTransport({"/a/b": ["/a/b/x.txt"], "/a__b": ["/a__b/y.txt"],
                                   "/index": ["/index/z.txt"]})
        code, stats = self.run_spike(transport, roots=["/a/b", "/a__b", "/index"])
        self.assertEqual(code, 0)
        documents = list(Path(stats["output_dir"]).glob("*.md"))
        self.assertEqual(len(documents), 4)
        contents = [p.read_text() for p in documents if p.name != "index.md"]
        for path in ("/a/b", "/a__b", "/index"):
            self.assertTrue(any(md.startswith(f"# {path}\n") for md in contents))

    def test_rerun_preserves_previous_documents_and_checks_only_this_run(self):
        _, first = self.run_spike(FakeTransport({"/log": ["/log/old.txt"]}))
        old = {p: p.read_bytes() for p in (self.root / "out").rglob("*.md")}
        code, second = self.run_spike(FakeTransport({"/log": ["/log/new.txt"]}))
        self.assertEqual(code, 0)
        self.assertEqual({p: p.read_bytes() for p in old}, old)
        self.assertNotEqual(first["output_dir"], second["output_dir"])


if __name__ == "__main__":
    unittest.main()

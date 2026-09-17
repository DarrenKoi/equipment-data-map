"""Spike regressions with fake transport responses; no server or equipment needed."""

import contextlib
import io
import json
import sys
import tempfile
import tomllib
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

    def test_credentials_only_discovers_without_downloads_or_llm(self):
        config = self.root / "minimal.toml"
        config.write_text('[equipment]\nhost="fake"\nuser="ro"\npassword="ro-secret"\n'
                          f'[output]\ndir={json.dumps(str(self.root / "out"))}\n')
        transport = FakeTransport({"/": ["/log"], "/log": ["/log/a.txt"]})
        with patch.object(spike, "fleet_downloader", return_value=lambda **kw: transport), \
                patch.object(spike.requests, "post", side_effect=AssertionError("unexpected LLM call")), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = spike.main(config)
        self.assertEqual(code, 0)
        stats = json.loads(stdout.getvalue())
        self.assertEqual(stats["mode"], "metadata-only")
        self.assertEqual(stats["llm_calls"], 0)
        self.assertEqual(stats["bytes"], 0)
        self.assertIn(("list", "/log"), transport.calls)
        self.assertFalse(any(op == "download" for op, _ in transport.calls))
        documents = "\n".join(p.read_text() for p in Path(stats["output_dir"]).rglob("index.md"))
        self.assertIn("not configured", documents)

    def test_missing_credentials_stop_before_network_without_echoing_values(self):
        for missing in ("host", "user", "password"):
            with self.subTest(missing=missing):
                config = self.root / "missing.toml"
                values = {"host": "private-host", "user": "private-user", "password": "private-password"}
                values[missing] = ""
                config.write_text('[equipment]\n' + ''.join(f'{k}={json.dumps(v)}\n' for k, v in values.items()))
                with patch.object(spike, "fleet_downloader", side_effect=AssertionError("network")), \
                        contextlib.redirect_stdout(io.StringIO()) as stdout:
                    code = spike.main(config)
                self.assertEqual(code, 1)
                self.assertNotIn("private-", stdout.getvalue())

    def test_prepare_fills_blanks_preserves_credentials_and_existing_limits(self):
        config = self.root / "prepare.toml"
        password = 'secret"\\value\nsecond line'
        config.write_text('[equipment]\nhost="fake"\nuser="ro"\n'
                          f'password={json.dumps(password)}\nname=""\nroots=["/log"]\n'
                          '[budget]\nmax_download_bytes=0\nmax_dirs=3\n'
                          '[llm]\napi_key="private-key"\n')
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(spike.prepare_config(config), 0)
        cfg = tomllib.loads(config.read_text())
        self.assertEqual(cfg["equipment"]["password"], password)
        self.assertEqual(cfg["equipment"]["roots"], ["/log"])
        self.assertEqual(cfg["budget"]["max_download_bytes"], 0)
        self.assertEqual(cfg["budget"]["max_dirs"], 3)
        self.assertTrue(cfg["equipment"]["name"])
        self.assertEqual(cfg["llm"]["api_key"], "private-key")
        self.assertNotIn("private-key", stdout.getvalue())
        self.assertNotIn("secret", stdout.getvalue())
        before = config.read_bytes()
        spike.prepare_config(config)
        self.assertEqual(config.read_bytes(), before)

    def test_prepare_missing_or_empty_file_creates_defaults_without_credentials(self):
        for initial in (None, "", " \n\t", "# not configured yet\n"):
            with self.subTest(initial=initial):
                config = self.root / "empty.toml"
                config.unlink(missing_ok=True)
                if initial is not None:
                    config.write_text(initial)
                with patch.object(spike, "fleet_downloader", side_effect=AssertionError("network")), \
                        contextlib.redirect_stdout(io.StringIO()) as stdout:
                    self.assertEqual(spike.prepare_config(config), 0)
                status = json.loads(stdout.getvalue())
                self.assertFalse(status["config_ready"])
                self.assertEqual(status["missing_fields"], ["equipment.host", "equipment.user", "equipment.password"])
                cfg = tomllib.loads(config.read_text())
                self.assertEqual([cfg["equipment"][key] for key in ("host", "user", "password")], ["", "", ""])
                self.assertEqual(cfg["equipment"]["roots"], ["/"])
                self.assertEqual(cfg["budget"]["max_download_bytes"], 0)
                with patch.object(spike, "fleet_downloader", side_effect=AssertionError("network")), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(spike.main(config), 1)

    def test_prepare_partial_credentials_preserves_values_and_lists_only_missing(self):
        config = self.root / "partial-credentials.toml"
        config.write_text('[equipment]\nhost="private-host"\npassword="private-password"\n')
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(spike.prepare_config(config), 0)
        self.assertEqual(json.loads(stdout.getvalue())["missing_fields"], ["equipment.user"])
        self.assertNotIn("private-", stdout.getvalue())
        self.assertEqual(tomllib.loads(config.read_text())["equipment"]["password"], "private-password")

    def test_prepare_malformed_file_is_not_replaced(self):
        config = self.root / "broken.toml"
        original = '[equipment\npassword="private-password"'
        config.write_text(original)
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(spike.prepare_config(config), 1)
        self.assertEqual(config.read_text(), original)
        self.assertNotIn("private-password", stdout.getvalue())

    def test_minimal_discovery_stops_at_directory_limit(self):
        config = self.root / "bounded.toml"
        config.write_text('[equipment]\nhost="fake"\nuser="ro"\npassword="secret"\n'
                          f'[output]\ndir={json.dumps(str(self.root / "out"))}\n')
        tree = {"/": [f"/d{i}" for i in range(30)]}
        tree.update({f"/d{i}": [f"/d{i}/a.txt"] for i in range(30)})
        transport = FakeTransport(tree)
        with patch.object(spike, "fleet_downloader", return_value=lambda **kw: transport), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(spike.main(config), 0)
        stats = json.loads(stdout.getvalue())
        self.assertEqual(stats["dirs"], 20)
        self.assertIn("not visited", (Path(stats["output_dir"]) / "index.md").read_text())
        self.assertFalse(any(op == "download" for op, _ in transport.calls))

    def test_prepare_write_failure_preserves_original_and_removes_temporary(self):
        config = self.root / "preserved.toml"
        original = '[equipment]\nhost="fake"\nuser="ro"\npassword="secret"\n'
        config.write_text(original)
        with patch.object(spike.os, "replace", side_effect=OSError("private-secret")), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(spike.prepare_config(config), 1)
        self.assertEqual(config.read_text(), original)
        self.assertNotIn("private-secret", stdout.getvalue())
        self.assertEqual(list(self.root.glob(".equipment-*.tmp")), [])

    def test_partial_llm_configuration_stops_before_network(self):
        config = self.root / "partial.toml"
        config.write_text('[equipment]\nhost="fake"\nuser="ro"\npassword="secret"\n'
                          '[llm]\nurl="http://private"\n')
        with patch.object(spike, "fleet_downloader", side_effect=AssertionError("network")), \
                contextlib.redirect_stdout(io.StringIO()) as stdout:
            self.assertEqual(spike.main(config), 1)
        self.assertNotIn("http://private", stdout.getvalue())

    def test_invalid_optional_settings_stop_before_network(self):
        for extra in ('roots="/log"', 'name="../outside"', 'port=0',
                      '[budget]\nmax_dirs=-1', '[llm]\ntimeout_s=nan'):
            with self.subTest(extra=extra):
                config = self.root / "invalid.toml"
                config.write_text('[equipment]\nhost="fake"\nuser="ro"\npassword="secret"\n' + extra)
                with patch.object(spike, "fleet_downloader", side_effect=AssertionError("network")), \
                        contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(spike.main(config), 1)

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

    def test_absolute_deny_pattern_is_scoped_to_one_root_and_blocks_subtree(self):
        transport = FakeTransport({
            "/target-a": [
                "/target-a/MACFILE",
                "/target-a/MACFILE_2024",
                "/target-a/MACFILE_2024/untrusted.log",
            ],
            "/target-a/MACFILE": ["/target-a/MACFILE/current.log"],
            "/target-a/MACFILE_2024": ["/target-a/MACFILE_2024/backup.log"],
            "/target-b": ["/target-b/MACFILE_2024"],
            "/target-b/MACFILE_2024": ["/target-b/MACFILE_2024/current.log"],
        })
        self.run_spike(
            transport,
            roots=["/target-a", "/target-b"],
            deny=["/target-a/MACFILE_*"],
        )
        touched = {path for _, path in transport.calls}
        self.assertFalse(any(path.startswith("/target-a/MACFILE_2024") for path in touched))
        self.assertIn("/target-a/MACFILE", touched)
        self.assertIn("/target-b/MACFILE_2024", touched)

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

    def test_output_mirrors_remote_folders_with_one_index_per_directory(self):
        transport = FakeTransport({"/a/b": ["/a/b/x.txt"], "/a__b": ["/a__b/y.txt"],
                                   "/index.md": ["/index.md/z.txt"], "/q:r": ["/q:r/w.txt"]})
        code, stats = self.run_spike(transport, roots=["/a/b", "/a__b", "/index.md", "/q:r"])
        self.assertEqual(code, 0)
        run = Path(stats["output_dir"])
        pages = {p.parent.relative_to(run).as_posix(): p.read_text() for p in run.rglob("index.md")}
        self.assertEqual(set(pages), {".", "a", "a/b", "a__b", "%69ndex.md", "q%3Ar"})
        for folder, path in (("a/b", "/a/b"), ("a__b", "/a__b"),
                             ("%69ndex.md", "/index.md"), ("q%3Ar", "/q:r")):
            self.assertTrue(pages[folder].startswith(f"# {path}\n"), folder)
        self.assertIn("(%2569ndex.md/index.md)", pages["."])
        self.assertIn("(q%253Ar/index.md)", pages["."])
        self.assertIn("[b](b/index.md)", pages["a"])
        self.assertIn("[..](../index.md)", pages["a/b"])
        self.assertIn("not inventoried", pages["a"])

    def test_case_twin_directory_is_not_visited_and_parent_says_why(self):
        transport = FakeTransport({"/eq": ["/eq/Logs", "/eq/logs"],
                                   "/eq/Logs": ["/eq/Logs/a.txt"], "/eq/logs": ["/eq/logs/b.txt"]})
        code, stats = self.run_spike(transport, roots=["/eq"])
        self.assertEqual(code, 0)
        self.assertNotIn(("list", "/eq/logs"), transport.calls)
        parent = (Path(stats["output_dir"]) / "eq" / "index.md").read_text()
        self.assertIn("| [Logs](Logs/index.md) | - |", parent)
        self.assertIn("| logs | case-collision |", parent)

    def test_too_long_directory_is_not_visited(self):
        deep = "/" + "d" * 130
        transport = FakeTransport({deep: [deep + "/a.txt"]})
        _, stats = self.run_spike(transport, roots=[deep])
        self.assertEqual(transport.calls, [])
        self.assertIn("path-too-long", (Path(stats["output_dir"]) / "index.md").read_text())

    def test_local_names_are_windows_safe_and_reversible(self):
        cases = {"a:b": "a%3Ab", "50%": "50%25", "x*?": "x%2A%3F", "tab\tname": "tab%09name",
                 "end.": "end%2E", "end. ": "end%2E%20", "...": "%2E%2E%2E",
                 "NUL.txt": "%4EUL.txt", "com\u00b9": "%63om\u00b9", "Index.MD": "%49ndex.MD",
                 "\ub85c\uadf8": "\ub85c\uadf8",
                 "nullable.log": "nullable.log", "CONFIG": "CONFIG"}
        for remote, local in cases.items():
            self.assertEqual(spike.local_name(remote), local, remote)

    def test_rerun_preserves_previous_documents_and_checks_only_this_run(self):
        _, first = self.run_spike(FakeTransport({"/log": ["/log/old.txt"]}))
        old = {p: p.read_bytes() for p in (self.root / "out").rglob("*.md")}
        code, second = self.run_spike(FakeTransport({"/log": ["/log/new.txt"]}))
        self.assertEqual(code, 0)
        self.assertEqual({p: p.read_bytes() for p in old}, old)
        self.assertNotEqual(first["output_dir"], second["output_dir"])


if __name__ == "__main__":
    unittest.main()

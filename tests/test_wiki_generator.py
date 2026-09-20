"""Synthetic end-to-end checks for publication, tracking, and review iterations."""
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote

import pytest


from tools.wiki_demo import create_demo_map as fixture_map, digest, canonical, write_json, reindex


def modules():
    assert importlib.util.find_spec('wiki_review.publish') is not None, 'Wiki generator is not implemented'
    from wiki_review.publish import DataMap, publish
    from wiki_review.exploration import Journal
    return DataMap, publish, Journal


def test_navigation_and_sample_summaries_are_deterministic_and_input_is_unchanged(tmp_path):
    DataMap, publish, Journal = modules()
    source = fixture_map(tmp_path/'map')
    before = {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}
    model = DataMap(source)
    log = Journal(tmp_path/'review.sqlite')
    publish(model, tmp_path/'review-1', log, iteration=1)
    publish(model, tmp_path/'review-copy', log, iteration=1)
    page = (tmp_path/'review-1/wiki/Data/Logs/index.md').read_text()
    assert page.index('## 이 폴더는 무엇인가') < page.index('## 대표 파일')
    assert 'temperature' in page and 'csv' in page and '부분 관측' in page
    assert 'fixture-secret-987' not in page and '(masked)' in page
    assert 'Temperature record (inferred)' in page
    assert 'Temperature record (inferred)' not in page.split('### Observed')[1].split('### Inferred')[0]
    parent = (tmp_path/'review-1/wiki/Data/index.md').read_text()
    assert 'a%253Ab/index.md' in parent and 'csv' in parent
    for file in (tmp_path/'review-1/wiki').rglob('*.md'):
        for link in re.findall(r'\]\(([^)]+)\)', file.read_text()):
            assert (file.parent/unquote(link)).is_file()
    for file in (tmp_path/'review-1').rglob('*'):
        if file.is_file():
            assert file.read_bytes() == (tmp_path/'review-copy'/file.relative_to(tmp_path/'review-1')).read_bytes()
    assert before == {p.relative_to(source): p.read_bytes() for p in source.rglob('*') if p.is_file()}


def test_page_read_is_not_sample_interpretation_and_iterations_close_only_new_completed_work(tmp_path):
    DataMap, publish, Journal = modules()
    model = DataMap(fixture_map(tmp_path/'map'))
    log = Journal(tmp_path/'review.sqlite')
    path = '/Data/Logs/run.csv'
    log.suggest(model, path, 'Important temperature evidence was missed', 'engineer', 1)
    log.suggest(model, '/Data/Logs/running.lock', 'Important but protected', 'llm', 1)
    publish(model, tmp_path/'review-1', log, iteration=1)
    content = log.read_page(tmp_path/'review-1', 'Data/Logs/index.md', 'llm')
    assert '대표 파일' in content
    assert log.plan(model)['items_by_path'][path]['action'] == 'interpret'
    log.submitted(model, 'request-1', [path], 'qwen', 2)
    assert log.plan(model)['items_by_path'][path]['status'] == 'pending'
    log.finished(model.scope, 'request-1', 'succeeded')
    plan = log.plan(model)
    assert plan['items_by_path'][path]['status'] == 'addressed'
    assert plan['items_by_path']['/Data/Logs/running.lock']['status'] == 'blocked'
    assert plan['items_by_path']['/Data/Logs/missed.csv']['action'] == 'review-sampling'
    log.suggest(model, path, 'Recheck this meaning', 'engineer', 2)
    assert log.plan(model)['items_by_path'][path]['status'] == 'pending'
    publish(model, tmp_path/'review-2', log, iteration=2)
    assert (tmp_path/'review-1/wiki/Data/Logs/index.md').read_text() != (tmp_path/'review-2/wiki/Data/Logs/index.md').read_text()
    assert log.plan(model)['requires_approval'] is True
    assert len(log.events(model.scope)) == 6


def test_request_replay_conflict_failed_requests_and_changed_extracts(tmp_path):
    DataMap, publish, Journal = modules()
    root = fixture_map(tmp_path/'map')
    model, log = DataMap(root), Journal(tmp_path/'review.sqlite')
    path = '/Data/Logs/run.csv'
    log.submitted(model, 'r1', [path], 'qwen', 1)
    log.submitted(model, 'r1', [path], 'qwen', 1)
    assert len(log.events(model.scope)) == 1
    with pytest.raises(ValueError):log.submitted(model, 'r1', ['/Data/a:b/settings.csv'], 'qwen', 1)
    log.finished(model.scope, 'r1', 'failed')
    with pytest.raises(ValueError):log.finished(model.scope, 'r1', 'succeeded')
    assert log.plan(model)['items_by_path'][path]['status'] == 'pending'
    log.submitted(model, 'r2', [path], 'qwen', 2)
    log.finished(model.scope, 'r2', 'succeeded')
    assert log.plan(model)['items_by_path'][path]['status'] == 'addressed'
    rows = [json.loads(line) for line in (root/'extracts.jsonl').read_text().splitlines()]
    rows[0]['fields'][0]['unit'] = 'C'
    (root/'extracts.jsonl').write_bytes(b''.join(canonical(row)+b'\n' for row in rows))
    families = json.loads((root/'file-families.json').read_text())
    families[0]['samples'][0]['extract_sha256'] = digest(canonical(rows[0]))
    families[0]['interpretations'][0]['evidence'][0]['extract_sha256'] = digest(canonical(rows[0]))
    write_json(root/'file-families.json', families); reindex(root)
    assert log.plan(DataMap(root))['items_by_path'][path]['status'] == 'pending'
    other = DataMap(fixture_map(tmp_path/'other', 'scope-b'))
    assert log.events(other.scope) == []
    assert log.plan(other)['items_by_path'][path]['status'] == 'pending'


@pytest.mark.parametrize('damage', ['sample', 'foreign-citation', 'locator', 'traversal', 'collision', 'symlink', 'observed-llm'])
def test_invalid_or_unsafe_input_is_rejected_before_any_output(tmp_path, damage):
    DataMap, publish, Journal = modules()
    root = fixture_map(tmp_path/'map')
    families = json.loads((root/'file-families.json').read_text())
    if damage == 'sample':(root/'evidence/Data/Logs/run.csv').write_bytes(b'tampered')
    elif damage == 'foreign-citation': families[0]['interpretations'][0]['evidence'] = families[1]['interpretations'][0]['evidence']
    elif damage == 'locator': families[0]['interpretations'][0]['evidence'][0]['locator'] = '/fields/999'
    elif damage == 'observed-llm':families[0]['interpretations'][0]['observed_vs_inferred'] = 'observed'
    elif damage in ('traversal', 'collision'):
        paths = json.loads((root/'paths.json').read_text())
        paths[2]['local_path'] = '../escape' if damage == 'traversal' else 'data'
        write_json(root/'paths.json', paths)
    elif damage == 'symlink':
        p = root/'evidence/Data/Logs/run.csv';p.unlink();p.symlink_to(root/'evidence/Data/a%3Ab/settings.csv')
    write_json(root/'file-families.json', families)
    if damage != 'sample':reindex(root)
    with pytest.raises(ValueError):DataMap(root)
    assert not (tmp_path/'output').exists()


def test_output_and_ledger_cannot_change_source_or_existing_review(tmp_path):
    DataMap, publish, Journal = modules()
    root = fixture_map(tmp_path/'map');model = DataMap(root)
    log = Journal(tmp_path/'review.sqlite')
    with pytest.raises(ValueError):publish(model, root/'wiki', log, iteration=1)
    with pytest.raises(ValueError):publish(model, tmp_path/'out', Journal(root/'bad.sqlite'), iteration=1)
    assert not (root/'bad.sqlite').exists()
    out = tmp_path/'out';out.mkdir();(out/'keep.txt').write_text('keep')
    with pytest.raises(ValueError):publish(model, out, log, iteration=1)
    assert (out/'keep.txt').read_text() == 'keep'
    with pytest.raises(ValueError):log.read_page(out, '../map/equipment.json', 'llm')


def test_cli_generates_wiki_without_network_or_model(tmp_path):
    modules()
    source = fixture_map(tmp_path/'map')
    result = subprocess.run([sys.executable, '-m', 'wiki_review.publish', str(source),
                             '--output', str(tmp_path/'review'), '--journal', str(tmp_path/'journal.sqlite'),
                             '--iteration', '1'], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '/Data' not in result.stdout and 'run.csv' not in result.stdout
    assert (tmp_path/'review/wiki/index.md').is_file()
    assert (tmp_path/'review/next-actions.json').is_file()


def test_folder_request_reopens_descendants_but_never_bypasses_exclusions(tmp_path):
    DataMap, publish, Journal = modules()
    model = DataMap(fixture_map(tmp_path/'map'))
    log = Journal(tmp_path/'journal.sqlite')
    path = '/Data/Logs/run.csv'
    log.submitted(model, 'old', [path], 'qwen', 1)
    log.finished(model.scope, 'old', 'succeeded')
    log.suggest(model, '/Data', 'Investigate this folder in detail', 'engineer', 2)
    plan = log.plan(model)
    assert plan['items_by_path'][path]['status'] == 'pending'
    assert plan['items_by_path']['/Data/a:b/settings.csv']['priority'] == 'requested'
    assert plan['items_by_path']['/Data/Logs/running.lock']['status'] == 'blocked'
    assert plan['folder_requests'][0]['frontier'] == ['/Data/Unknown']
    # Completing an earlier in-flight call cannot satisfy a later request.
    log.submitted(model, 'in-flight', [path], 'qwen', 2)
    log.suggest(model, '/Data/Logs', 'Check again with revised question', 'engineer', 3)
    log.finished(model.scope, 'in-flight', 'succeeded')
    assert log.plan(model)['items_by_path'][path]['status'] == 'pending'
    log.submitted(model, 'new', [path], 'qwen', 3)
    log.finished(model.scope, 'new', 'succeeded')
    assert log.plan(model)['items_by_path'][path]['status'] == 'addressed'
    assert log.plan(model)['folder_requests'][0]['status'] == 'pending'
    with pytest.raises(ValueError):log.suggest(model, '/Outside', 'Investigate', 'llm', 3)
    with pytest.raises(ValueError):log.submitted(model, 'denied', ['/Data/Logs/running.lock'], 'qwen', 3)


def test_literal_data_masking_and_tampered_wiki_read(tmp_path):
    DataMap, publish, Journal = modules()
    root = fixture_map(tmp_path/'map')
    families = json.loads((root/'file-families.json').read_text())
    families[0]['interpretations'][0]['value'] = 'fixture-secret-987\n<script>bad</script> ` [[link]] ![x](https://evil.invalid)'
    write_json(root/'file-families.json', families);reindex(root)
    model, log = DataMap(root), Journal(tmp_path/'journal.sqlite')
    output = tmp_path/'review';publish(model, output, log, 1)
    target = output/'wiki/Data/Logs/index.md'
    text = target.read_text()
    assert 'fixture-secret-987' not in text
    assert '\\u000a' in text and '`` ' in text
    target.write_text(text+'tampered')
    with pytest.raises(ValueError):log.read_page(output, 'Data/Logs/index.md', 'llm')
    assert log.events(model.scope) == []


def test_metadata_only_family_stays_unresolved(tmp_path):
    DataMap, publish, Journal = modules()
    root = fixture_map(tmp_path/'map')
    families = json.loads((root/'file-families.json').read_text())
    families[0]['samples'] = [];families[0]['interpretations'] = []
    write_json(root/'file-families.json', families)
    rows = (root/'extracts.jsonl').read_bytes().splitlines()
    (root/'extracts.jsonl').write_bytes(rows[1]+b'\n');reindex(root)
    model, log = DataMap(root), Journal(tmp_path/'journal.sqlite')
    publish(model, tmp_path/'review', log, 1)
    assert '표본 없음' in (tmp_path/'review/wiki/Data/Logs/index.md').read_text()
    assert log.plan(model)['items_by_path']['/Data/Logs/run.csv']['sampling_bucket'] == 'pending-pass'


def test_short_secret_value_does_not_corrupt_provenance_identifiers(tmp_path):
    DataMap, publish, Journal = modules()
    root = fixture_map(tmp_path/'map')
    rows = [json.loads(line) for line in (root/'extracts.jsonl').read_text().splitlines()]
    rows[0]['fields'][1]['examples'] = ['1']
    (root/'extracts.jsonl').write_bytes(b''.join(canonical(row)+b'\n' for row in rows))
    families = json.loads((root/'file-families.json').read_text())
    sample = families[0]['samples'][0]
    sample['extract_sha256'] = digest(canonical(rows[0]))
    families[0]['interpretations'][0]['evidence'][0]['extract_sha256'] = sample['extract_sha256']
    write_json(root/'file-families.json', families);reindex(root)
    publish(DataMap(root), tmp_path/'review', Journal(tmp_path/'journal.sqlite'), 1)
    text = (tmp_path/'review/wiki/Data/Logs/index.md').read_text()
    assert sample['sha256'] in text and sample['extract_sha256'] in text
    assert sample['observation_id'] in text
    assert '12.4' in text and '13.5' in text
    assert "{'string': 1}" in text


def test_engineer_eligibility_and_folder_residuals_are_respected(tmp_path):
    DataMap, publish, Journal = modules()
    # Eligibility is exported after the engineer's policy exceptions are applied.
    model = DataMap(fixture_map(tmp_path/'map', log_name='temperature.csv'))
    log = Journal(tmp_path/'journal.sqlite')
    path = '/Data/Logs/temperature.csv'
    log.suggest(model, '/Data/Logs', 'Investigate', 'engineer', 1)
    log.submitted(model, 'r1', [path], 'qwen', 1)
    log.finished(model.scope, 'r1', 'succeeded')
    plan = log.plan(model)
    assert plan['items_by_path'][path]['status'] == 'addressed'
    folder = plan['folder_requests'][0]
    assert folder['status'] == 'review-required'
    assert folder['residual'] == {'blocked': 1, 'family-capped': 1}
    assert not any(v['action'] == 'interpret' and v['status'] == 'pending'
                   for p, v in plan['items_by_path'].items() if p.startswith('/Data/Logs/'))

"""Create synthetic review inputs and demonstrate a folder follow-up without a model."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def create_demo_map(root, scope='scope-a', log_name='run.csv'):
    root.mkdir()
    paths = [('/', '', 'ancestor'), ('/Data', 'Data', 'inventoried'),
             ('/Data/Logs', 'Data/Logs', 'inventoried'),
             ('/Data/a:b', 'Data/a%3Ab', 'inventoried'),
             ('/Data/Unknown', 'Data/Unknown', 'frontier')]
    families, extracts, metadata = [], [], []
    for fid, folder, name in [('logs', '/Data/Logs', log_name), ('config', '/Data/a:b', 'settings.csv')]:
        source = folder + '/' + name
        local = 'evidence/' + folder[1:].replace(':', '%3A') + '/' + name
        data = b'time,temperature\n1,12.4\n2,13.5\n'
        target = root / local
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        extract = {'scope': scope, 'source_path': source, 'observation_id': fid+'-1',
                   'sample_sha256': digest(data), 'method': 'csv', 'encoding': 'utf-8',
                   'truncated': True, 'fields': [
                       {'name': 'temperature', 'type_counts': {'float': 2}, 'unit': None,
                        'min': 12.4, 'max': 13.5, 'examples': [12.4, 13.5]},
                       {'name': 'db_password', 'type_counts': {'string': 1}, 'unit': None,
                        'min': None, 'max': None, 'examples': ['fixture-secret-987']}]}
        extracts.append(extract)
        rows = [{'source_path': source, 'observation_id': fid+'-1', 'size': len(data), 'status': 'eligible'},
                {'source_path': folder+'/missed.csv', 'observation_id': fid+'-2', 'size': 100, 'status': 'eligible'},
                {'source_path': folder+'/running.lock', 'observation_id': fid+'-3', 'size': 10, 'status': 'denied'}]
        meta = {'scope': scope, 'family_id': fid, 'entries': rows}
        metadata.append(meta)
        sample = {'source_path': source, 'local_path': local, 'sha256': digest(data),
                  'observation_id': fid+'-1', 'extract_sha256': digest(canonical(extract))}
        citation = {'evidence_kind': 'sample', 'source_path': source, 'sha256': sample['sha256'],
                    'observation_id': fid+'-1', 'extract_sha256': sample['extract_sha256'], 'locator': '/fields/0'}
        families.append({'family_id': fid, 'scope': scope, 'directory': folder,
                         'rule': '*.csv', 'kind': 'loose', 'member_count': 3,
                         'samples': [sample], 'metadata_evidence': digest(canonical(meta)),
                         'interpretations': [{'claim_id': fid+'-meaning', 'value': 'Temperature record (inferred)',
                                              'observed_vs_inferred': 'inferred', 'confidence': 'medium',
                                              'evidence': [citation]}], 'relationships': [], 'unresolved': []})
    write_json(root/'equipment.json', {'schema_version': 'wiki-map-v1', 'scope': scope, 'pass_id': 1, 'roots': ['/Data']})
    write_json(root/'paths.json', [{'source_path': path, 'local_path': local, 'status': status} for path, local, status in paths])
    write_json(root/'file-families.json', families)
    write_json(root/'coverage.json', {'inventory_complete': False, 'stop_reasons': ['max_entries']})
    for name, rows in [('extracts.jsonl', extracts), ('metadata-evidence.jsonl', metadata)]:
        (root/name).write_bytes(b''.join(canonical(row)+b'\n' for row in rows))
    reindex(root)
    return root


def reindex(root):
    files = {str(p.relative_to(root)).replace('\\', '/'): digest(p.read_bytes())
             for p in sorted(root.rglob('*')) if p.is_file() and p.name != 'index.json'}
    write_json(root/'index.json', {'schema_version': 'wiki-map-v1', 'files': files})



def main():
    from wiki_review.exploration import Journal
    from wiki_review.publish import DataMap, publish
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Choose a new output directory')
    args.output.mkdir(parents=True)
    model = DataMap(create_demo_map(args.output / 'map'))
    journal = Journal(args.output / 'exploration.sqlite')
    publish(model, args.output / 'iteration-1', journal, 1)
    journal.read_page(args.output / 'iteration-1', 'Data/Logs/index.md', 'demo-reader')
    journal.suggest(model, '/Data/Logs', 'Investigate error conditions in more detail', 'demo-engineer', 2)
    journal.submitted(model, 'simulated-call', ['/Data/Logs/run.csv'], 'demo-worker', 2)
    journal.finished(model.scope, 'simulated-call', 'succeeded')
    publish(model, args.output / 'iteration-2', journal, 2)
    print('Created two synthetic review iterations. No FTP or LLM calls were made.')


if __name__ == '__main__':
    main()

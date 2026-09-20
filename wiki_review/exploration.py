"""Local review journal: reported LLM work, Wiki reads, and follow-up requests."""
import argparse
from collections import Counter
import json
from pathlib import Path, PurePosixPath
import sqlite3

from wiki_review.publish import DataMap, canonical, digest, safe_file, source_path, under


class Journal:
    def __init__(self, path):
        candidate = Path(path).absolute()
        self.path = candidate.parent.resolve() / candidate.name

    def guard(self, model):
        if self.path.resolve().is_relative_to(model.root):
            raise ValueError('Journal must be outside the source map')
        safe_file(Path(self.path.anchor), self.path.relative_to(self.path.anchor).as_posix())

    def connect(self):
        safe_file(Path(self.path.anchor), self.path.relative_to(self.path.anchor).as_posix())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        db.execute('PRAGMA synchronous=FULL')
        db.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, scope TEXT NOT NULL, kind TEXT NOT NULL, request_id TEXT, payload TEXT NOT NULL)')
        db.execute('CREATE UNIQUE INDEX IF NOT EXISTS requests ON events(scope,kind,request_id) WHERE request_id IS NOT NULL')
        return db

    def events(self, scope):
        if not self.path.exists():
            return []
        db = self.connect()
        try:
            return [dict(id=row[0], kind=row[1], **json.loads(row[2])) for row in db.execute('SELECT id,kind,payload FROM events WHERE scope=? ORDER BY id', (scope,))]
        finally:
            db.close()

    def append(self, scope, kind, payload, request_id=None):
        raw = canonical(payload).decode('utf-8')
        db = self.connect()
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                if request_id is not None:
                    old = db.execute('SELECT payload FROM events WHERE scope=? AND kind=? AND request_id=?', (scope, kind, request_id)).fetchone()
                    if old:
                        if old[0] != raw:
                            raise ValueError('Conflicting replay of request')
                        return
                db.execute('INSERT INTO events(scope,kind,request_id,payload) VALUES(?,?,?,?)', (scope, kind, request_id, raw))
        finally:
            db.close()

    def suggest(self, model, path, reason, actor, iteration):
        self.guard(model)
        path = source_path(path)
        if path not in model.files and path not in model.paths:
            raise ValueError('Unknown file or folder; refresh inventory first')
        if not any(under(path, root) for root in model.roots):
            raise ValueError('Request outside allowed roots')
        if not reason.strip() or not actor.strip() or iteration < 1:
            raise ValueError('Request needs actor, reason and positive iteration')
        self.append(model.scope, 'suggestion', {'path': path, 'target': 'folder' if path in model.paths else 'file', 'reason': reason, 'actor': actor, 'iteration': iteration})

    def submitted(self, model, request_id, paths, actor, iteration):
        self.guard(model)
        if not request_id or not paths or len(paths) != len(set(paths)) or not actor or iteration < 1:
            raise ValueError('Invalid request identity')
        sources = {}
        for path in paths:
            if path not in model.samples:
                raise ValueError('Only verified samples can be submitted')
            sources[path] = model.samples[path]
        self.append(model.scope, 'submitted', {'request_id': request_id, 'sources': sources, 'actor': actor, 'iteration': iteration}, request_id)

    def finished(self, scope, request_id, outcome):
        if outcome not in ('succeeded', 'failed', 'unknown'):
            raise ValueError('Invalid outcome')
        if not any(e['kind'] == 'submitted' and e['request_id'] == request_id for e in self.events(scope)):
            raise ValueError('No recorded submission')
        self.append(scope, 'finished', {'request_id': request_id, 'outcome': outcome}, request_id)

    def plan(self, model):
        self.guard(model)
        # ponytail: scan one journal snapshot; index per-path events if large histories become slow.
        events = self.events(model.scope)
        suggestions = [e for e in events if e['kind'] == 'suggestion']
        finished = {e['request_id']: e for e in events if e['kind'] == 'finished'}
        items = {}
        for path, entry in sorted(model.files.items()):
            requests = [e for e in suggestions if e['path'] == path or (e['target'] == 'folder' and under(path, e['path']))]
            latest_request = max((e['id'] for e in requests), default=0)
            completed = []
            submissions = [e for e in events if e['kind'] == 'submitted' and path in e['sources']]
            for event in submissions:
                result = finished.get(event['request_id'])
                if result and result['outcome'] == 'succeeded' and event['id'] > latest_request and event['sources'][path] == model.samples.get(path):
                    completed.append(result['id'])
            blocked = entry['status'] != 'eligible'
            has_sample = path in model.samples
            family_sampled = any(model.files[p]['family_id'] == entry['family_id'] for p in model.samples)
            items[path] = {'family_id': entry['family_id'],
                           'status': 'blocked' if blocked else 'addressed' if completed else 'pending',
                           'action': 'blocked' if blocked else 'none' if completed else 'interpret' if has_sample else 'review-sampling',
                           'sampling_bucket': 'blocked' if blocked else 'sampled' if has_sample else 'family-capped' if family_sampled else 'pending-pass',
                           'reason': entry['status'] if blocked else 'producer-reported completion' if completed else 'review required',
                           'priority': 'requested' if requests else 'normal',
                           'suggestions': requests, 'reported_submissions': len(submissions)}
        folders = []
        for event in suggestions:
            if event['target'] == 'folder':
                frontier = [p for p, row in model.paths.items() if under(p, event['path']) and row['status'] == 'frontier']
                descendants = [v for p, v in items.items() if under(p, event['path'])]
                actionable = [v for v in descendants if v['sampling_bucket'] == 'sampled']
                residual = dict(sorted(Counter(v['sampling_bucket'] for v in descendants if v['sampling_bucket'] != 'sampled').items()))
                status = 'pending' if frontier or any(v['status'] != 'addressed' for v in actionable) else 'review-required' if residual else 'addressed'
                folders.append(dict(event, status=status, frontier=frontier, residual=residual))
        return {'scope': model.scope, 'source_index_sha256': model.revision, 'requires_approval': True,
                'approval_verified': False, 'items_by_path': items, 'folder_requests': folders,
                'wiki_reads': [e for e in events if e['kind'] == 'page-read'],
                'coverage': model.coverage,
                'limitations': ['Known inventory only; no estimate of undiscovered files.',
                                'Review queue only: no collection, policy override, or model invocation.',
                                'Completion is producer-reported, not proof of semantic correctness.']}

    def read_page(self, output, relative, actor):
        root = Path(output).resolve()
        if self.path.resolve().is_relative_to(root):
            raise ValueError('Journal must be outside publication')
        target = safe_file(root / 'wiki', relative)
        if PurePosixPath(relative).name != 'index.md':
            raise ValueError('Only generated folder pages can be read')
        manifest = json.loads(safe_file(root, 'manifest.json').read_bytes())
        data = target.read_bytes()
        if manifest['files'].get('wiki/' + relative) != digest(data):
            raise ValueError('Wiki page hash mismatch')
        self.append(manifest['scope'], 'page-read', {'page': relative, 'sha256': digest(data), 'actor': actor,
                                                  'iteration': manifest['iteration'], 'source_index_sha256': manifest['source_index_sha256']})
        return data.decode('utf-8')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--journal', type=Path, required=True)
    commands = parser.add_subparsers(dest='command', required=True)
    for name in ('suggest', 'submitted', 'plan'):
        p = commands.add_parser(name)
        p.add_argument('map', type=Path)
        if name != 'plan':
            p.add_argument('--actor', required=True)
            p.add_argument('--iteration', type=int, required=True)
        if name == 'suggest':
            p.add_argument('--path', required=True)
            p.add_argument('--reason', required=True)
        elif name == 'submitted':
            p.add_argument('--request-id', required=True)
            p.add_argument('--path', action='append', required=True)
    p = commands.add_parser('finished')
    p.add_argument('--scope', required=True)
    p.add_argument('--request-id', required=True)
    p.add_argument('--outcome', choices=('succeeded', 'failed', 'unknown'), required=True)
    p = commands.add_parser('read-page')
    p.add_argument('output', type=Path)
    p.add_argument('--page', required=True)
    p.add_argument('--actor', required=True)
    args = parser.parse_args()
    journal = Journal(args.journal)
    try:
        if args.command in ('suggest', 'submitted', 'plan'):
            model = DataMap(args.map)
        if args.command == 'suggest':
            journal.suggest(model, args.path, args.reason, args.actor, args.iteration)
        elif args.command == 'submitted':
            journal.submitted(model, args.request_id, args.path, args.actor, args.iteration)
        elif args.command == 'plan':
            print(json.dumps(journal.plan(model), ensure_ascii=False, indent=2))
        elif args.command == 'finished':
            journal.finished(args.scope, args.request_id, args.outcome)
        else:
            print(journal.read_page(args.output, args.page, args.actor), end='')
    except (ValueError, OSError, KeyError, sqlite3.Error) as exc:
        parser.exit(2, f'Review operation rejected: {type(exc).__name__}\n')


if __name__ == '__main__':
    main()

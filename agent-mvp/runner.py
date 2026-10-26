"""AJAR bounded proposal runner. Never executes generated code."""
import argparse
import base64
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import urllib.request

ROOT = Path(__file__).resolve().parent
REPO = 'exgoya/ajar-core'
LIMIT = 24000
OUTPUT = 3000


def api(path, method='GET', data=None):
    return request('https://api.github.com/' + path, os.environ['GH_TOKEN'], method, data)


def request(url, token, method, data):
    req = urllib.request.Request(url, method=method,
        data=None if data is None else json.dumps(data).encode(),
        headers={'Authorization': 'Bearer ' + token, 'Content-Type': 'application/json',
                 'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.load(response)


def validate_files(files):
    if not isinstance(files, list) or not 1 <= len(files) <= 8:
        raise ValueError('Expected 1..8 files')
    seen = set()
    for item in files:
        if set(item) != {'path', 'content'}:
            raise ValueError('Unexpected file fields')
        path, content = item['path'], item['content']
        if not isinstance(path, str) or not re.fullmatch(r'agent-mvp/(app|app_tests)/[a-zA-Z0-9_/]+\.py', path):
            raise ValueError('Only app/ and app_tests/ Python files may change')
        if path in seen or '..' in PurePosixPath(path).parts or not isinstance(content, str) or len(content.encode()) > 12000:
            raise ValueError('Duplicate, unsafe, or oversized file')
        seen.add(path)
        if re.search(r'(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY)', content):
            raise ValueError('Potential secret')
    if not any(p.startswith('agent-mvp/app_tests/test_') for p in seen):
        raise ValueError('At least one test required')
    return files


def reserve_cost():
    # Deliberately pessimistic byte-based token bound, including message overhead.
    rates = [float(os.environ[k]) for k in ('AJAR_INPUT_USD_M', 'AJAR_OUTPUT_USD_M')]
    budget = float(os.environ['AJAR_RUN_USD'])
    if not all(math.isfinite(x) and x > 0 for x in [*rates, budget]):
        raise ValueError('Positive finite verified prices and budget required')
    ceiling = 4 * ((LIMIT + 4096) * rates[0] + OUTPUT * rates[1]) / 1000000
    if ceiling > budget:
        raise ValueError('Worst-case reservation exceeds run budget')
    return ceiling


def model(role, context, schema):
    brand = (ROOT.parent / 'docs' / 'brand-draft.md').read_text()
    prompt = (ROOT / 'prompts' / (role + '.md')).read_text()
    prompt += '\nAJAR 브랜드 방향 (docs/brand-draft.md):\n' + brand
    data = json.dumps(context, ensure_ascii=False)
    if len((prompt + data).encode()) > LIMIT:
        raise ValueError('Context too large; stopped before API call')
    payload = {'model': os.environ['OPENAI_MODEL'], 'store': False, 'max_output_tokens': OUTPUT,
        'instructions': prompt, 'input': data,
        'text': {'format': {'type': 'json_schema', 'name': role, 'strict': True, 'schema': schema}}}
    result = request('https://api.openai.com/v1/responses', os.environ['OPENAI_API_KEY'], 'POST', payload)
    if result.get('status') != 'completed':
        raise ValueError('Incomplete model response; no retry')
    output = ''.join(c['text'] for m in result.get('output', []) if m.get('type') == 'message'
                     for c in m.get('content', []) if c.get('type') == 'output_text')
    return json.loads(output)


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


TEXT = {'type': 'string'}
REPORT = obj({'decision': {'type': 'string', 'enum': ['proceed', 'stop']}, 'reason': TEXT})
PLAN = obj({'scope': TEXT, 'acceptance': TEXT, 'risks': TEXT})
FILES = obj({'files': {'type': 'array', 'items': obj({'path': TEXT, 'content': TEXT})}})


def run(issue_number):
    if not re.fullmatch(r'[1-9][0-9]*', issue_number):
        raise ValueError('Positive issue number required')
    if os.environ.get('GITHUB_REPOSITORY') != REPO or os.environ.get('GITHUB_REF') != 'refs/heads/main' or os.environ.get('GITHUB_ACTOR') != 'exgoya':
        raise ValueError('Only exgoya on ajar-core main may run')
    if os.environ.get('AJAR_ENABLED') != 'true':
        raise ValueError('Kill switch is off')
    ceiling = reserve_cost()
    issue = api(f'repos/{REPO}/issues/{issue_number}')
    if issue.get('state') != 'open' or 'pull_request' in issue or 'agent:approved' not in [x['name'] for x in issue['labels']]:
        raise ValueError('Open issue with human approval label required')
    branch = f'agent/issue-{issue_number}'
    base = api(f'repos/{REPO}/git/ref/heads/main')['object']['sha']
    # Atomic durable lock BEFORE any paid call. Existing branch means fail closed,
    # including failed previous runs. Never delete automatically or force-push.
    api(f'repos/{REPO}/git/refs', 'POST', {'ref': 'refs/heads/' + branch, 'sha': base})
    context = {'issue': {'title': issue['title'], 'body': issue.get('body') or ''}}
    if model('orchestrator', context, REPORT)['decision'] != 'proceed':
        raise ValueError('Orchestrator stopped')
    context['plan'] = model('planning', context, PLAN)
    # Deliberately scoped to new independent modules; existing source is not sent.
    files = validate_files(model('developer', context, FILES)['files'])
    review = model('review', {**context, 'files': files}, REPORT)
    if review['decision'] != 'proceed':
        raise ValueError('Review stopped')
    tree = api(f'repos/{REPO}/git/commits/{base}')['tree']['sha']
    existing = api(f'repos/{REPO}/git/trees/{tree}?recursive=1')
    if existing.get('truncated'):
        raise ValueError('Cannot inspect complete tree')
    paths = {x['path'] for x in existing['tree']}
    if any(f['path'] in paths for f in files):
        raise ValueError('MVP adds files only; existing path needs manual review')
    entries = [{'path': f['path'], 'mode': '100644', 'type': 'blob', 'content': f['content']} for f in files]
    new_tree = api(f'repos/{REPO}/git/trees', 'POST', {'base_tree': tree, 'tree': entries})['sha']
    commit = api(f'repos/{REPO}/git/commits', 'POST', {'message': f'AJAR issue #{issue_number}', 'tree': new_tree, 'parents': [base]})['sha']
    api(f'repos/{REPO}/git/refs/heads/{branch}', 'PATCH', {'sha': commit, 'force': False})
    body = f'Closes #{issue_number}\n\n' + json.dumps({'plan': context['plan'], 'review': review, 'reserved_usd': ceiling}, ensure_ascii=False, indent=2)
    body += '\n\nAI review is advisory. Run Agent verification on this branch, inspect tests and approve manually. No automatic merge.'
    pr = api(f'repos/{REPO}/pulls', 'POST', {'title': f'AJAR: Issue #{issue_number}', 'head': branch, 'base': 'main', 'body': body, 'draft': True})
    print(pr['html_url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--issue', required=True)
    args = parser.parse_args()
    try:
        run(args.issue)
    except Exception as error:
        # Never expose model output, HTTP response bodies, or secret-bearing errors.
        print('Stopped safely: ' + type(error).__name__ + '. Inspect branch and run state before recovery.')
        raise SystemExit(1)

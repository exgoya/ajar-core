"""AJAR bounded proposal runner. Never executes generated code."""
import argparse
import base64
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import urllib.request
import urllib.error

ROOT = Path(__file__).resolve().parent
REPO = 'exgoya/ajar-core'
LIMIT = 24000
OUTPUT = 3000


STAGE = 'startup'
ATTEMPTS = 0
RESPONSES = 0


class SafeStop(ValueError):
    """Only fixed, developer-authored messages may be passed here."""


def stage(name):
    global STAGE
    STAGE = name
    print(f'AJAR stage={name}', flush=True)


def stopped(error):
    # Never interpolate arbitrary exception text, model content, URLs or headers.
    reason = str(error) if isinstance(error, SafeStop) else 'Unexpected error; inspect stage and error type'
    status = f' http_status={error.code}' if isinstance(error, urllib.error.HTTPError) else ''
    print(f'AJAR stopped stage={STAGE} error={type(error).__name__}{status} '
          f'api_attempts={ATTEMPTS} api_responses={RESPONSES} reason={reason}', flush=True)


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
        raise SafeStop('Expected 1..8 files')
    seen = set()
    for item in files:
        if set(item) != {'path', 'content'}:
            raise SafeStop('Unexpected file fields')
        path, content = item['path'], item['content']
        if not isinstance(path, str) or not re.fullmatch(r'agent-mvp/(app|app_tests)/[a-zA-Z0-9_/]+\.py', path):
            raise SafeStop('Only app/ and app_tests/ Python files may change')
        if path in seen or '..' in PurePosixPath(path).parts or not isinstance(content, str) or len(content.encode()) > 12000:
            raise SafeStop('Duplicate, unsafe, or oversized file')
        seen.add(path)
        if re.search(r'(sk-[A-Za-z0-9_-]{16,}|gh[pousr]_[A-Za-z0-9]{20,}|-----BEGIN .*PRIVATE KEY)', content):
            raise SafeStop('Potential secret')
    if not any(p.startswith('agent-mvp/app_tests/test_') for p in seen):
        raise SafeStop('At least one test required')
    return files


def reserve_cost():
    # Deliberately pessimistic byte-based token bound, including message overhead.
    rates = [float(os.environ[k]) for k in ('AJAR_INPUT_USD_M', 'AJAR_OUTPUT_USD_M')]
    budget = float(os.environ['AJAR_RUN_USD'])
    if not all(math.isfinite(x) and x > 0 for x in [*rates, budget]):
        raise SafeStop('Positive finite verified prices and budget required')
    ceiling = 4 * ((LIMIT + 4096) * rates[0] + OUTPUT * rates[1]) / 1000000
    if ceiling > budget:
        raise SafeStop('Worst-case reservation exceeds run budget')
    return ceiling


def model(role, context, schema):
    global ATTEMPTS, RESPONSES
    stage(role + '.prepare')
    brand = (ROOT.parent / 'docs' / 'brand-draft.md').read_text()
    prompt = (ROOT / 'prompts' / (role + '.md')).read_text()
    prompt += '\nAJAR 브랜드 방향 (docs/brand-draft.md):\n' + brand
    data = json.dumps(context, ensure_ascii=False)
    if len((prompt + data).encode()) > LIMIT:
        raise SafeStop('Context too large; stopped before API call')
    payload = {'model': os.environ['OPENAI_MODEL'], 'store': False, 'max_output_tokens': OUTPUT,
        'instructions': prompt, 'input': data,
        'text': {'format': {'type': 'json_schema', 'name': role, 'strict': True, 'schema': schema}}}
    stage(role + '.api_request')
    ATTEMPTS += 1
    result = request('https://api.openai.com/v1/responses', os.environ['OPENAI_API_KEY'], 'POST', payload)
    RESPONSES += 1
    stage(role + '.api_response')
    print(f'AJAR api_response_received role={role}', flush=True)
    usage = result.get('usage') or {}
    counts = {k: usage[k] for k in ('input_tokens', 'output_tokens', 'total_tokens')
              if type(usage.get(k)) is int and usage[k] >= 0}
    if counts:
        print('AJAR usage=' + json.dumps(counts, sort_keys=True), flush=True)
    if result.get('status') != 'completed':
        raise SafeStop('Incomplete model response; no retry')
    stage(role + '.parse')
    output = ''.join(c['text'] for m in result.get('output', []) if m.get('type') == 'message'
                     for c in m.get('content', []) if c.get('type') == 'output_text')
    return json.loads(output)


def obj(properties):
    return {'type': 'object', 'properties': properties, 'required': list(properties), 'additionalProperties': False}


TEXT = {'type': 'string'}
REASON_CODES = ('allowed', 'scope_exceeded', 'ambiguous_requirements', 'security_concern',
                'brand_mismatch', 'implementation_bug', 'insufficient_tests', 'other')
REPORT = obj({'decision': {'type': 'string', 'enum': ['proceed', 'stop']},
              'reason_code': {'type': 'string', 'enum': list(REASON_CODES)}, 'reason': TEXT})


def check_decision(role, report):
    # Only schema-defined codes may reach logs, never arbitrary model reasoning.
    if role not in ('orchestrator', 'review'):
        raise SafeStop('Invalid decision role')
    stage(role + '.decision')
    if not isinstance(report, dict):
        raise SafeStop('Invalid decision report')
    decision, code = report.get('decision'), report.get('reason_code')
    if decision not in ('proceed', 'stop') or code not in REASON_CODES:
        raise SafeStop('Invalid decision or reason code')
    if (decision == 'proceed') != (code == 'allowed'):
        raise SafeStop('Inconsistent decision and reason code')
    print(f'AJAR decision role={role} decision={decision} reason_code={code}', flush=True)
    if decision == 'stop':
        # role and code are both checked against fixed values.
        raise SafeStop('Agent decision stopped; see reason_code')
PLAN = obj({'scope': TEXT, 'acceptance': TEXT, 'risks': TEXT})
FILES = obj({'files': {'type': 'array', 'items': obj({'path': TEXT, 'content': TEXT})}})


def run(issue_number):
    global ATTEMPTS, RESPONSES
    ATTEMPTS = RESPONSES = 0
    stage('preflight')
    if not re.fullmatch(r'[1-9][0-9]*', issue_number):
        raise SafeStop('Positive issue number required')
    if os.environ.get('GITHUB_REPOSITORY') != REPO or os.environ.get('GITHUB_REF') != 'refs/heads/main' or os.environ.get('GITHUB_ACTOR') != 'exgoya':
        raise SafeStop('Only exgoya on ajar-core main may run')
    if os.environ.get('AJAR_ENABLED') != 'true':
        raise SafeStop('Kill switch is off')
    stage('budget')
    ceiling = reserve_cost()
    stage('issue.read')
    issue = api(f'repos/{REPO}/issues/{issue_number}')
    if issue.get('state') != 'open' or 'pull_request' in issue or 'agent:approved' not in [x['name'] for x in issue['labels']]:
        raise SafeStop('Open issue with human approval label required')
    branch = f'agent/issue-{issue_number}'
    stage('branch.base')
    base = api(f'repos/{REPO}/git/ref/heads/main')['object']['sha']
    # Atomic durable lock BEFORE any paid call. Existing branch means fail closed,
    # including failed previous runs. Never delete automatically or force-push.
    stage('branch.lock')
    api(f'repos/{REPO}/git/refs', 'POST', {'ref': 'refs/heads/' + branch, 'sha': base})
    context = {'issue': {'title': issue['title'], 'body': issue.get('body') or ''}}
    stage('orchestrator')
    check_decision('orchestrator', model('orchestrator', context, REPORT))
    stage('planning')
    context['plan'] = model('planning', context, PLAN)
    # Deliberately scoped to new independent modules; existing source is not sent.
    stage('developer')
    generated = model('developer', context, FILES)['files']
    stage('files.validate')
    files = validate_files(generated)
    stage('review')
    review = model('review', {**context, 'files': files}, REPORT)
    check_decision('review', review)
    stage('files.collision_check')
    tree = api(f'repos/{REPO}/git/commits/{base}')['tree']['sha']
    existing = api(f'repos/{REPO}/git/trees/{tree}?recursive=1')
    if existing.get('truncated'):
        raise SafeStop('Cannot inspect complete tree')
    paths = {x['path'] for x in existing['tree']}
    if any(f['path'] in paths for f in files):
        raise SafeStop('MVP adds files only; existing path needs manual review')
    entries = [{'path': f['path'], 'mode': '100644', 'type': 'blob', 'content': f['content']} for f in files]
    stage('git.write')
    new_tree = api(f'repos/{REPO}/git/trees', 'POST', {'base_tree': tree, 'tree': entries})['sha']
    commit = api(f'repos/{REPO}/git/commits', 'POST', {'message': f'AJAR issue #{issue_number}', 'tree': new_tree, 'parents': [base]})['sha']
    api(f'repos/{REPO}/git/refs/heads/{branch}', 'PATCH', {'sha': commit, 'force': False})
    body = f'Closes #{issue_number}\n\n' + json.dumps({'plan': context['plan'], 'review': review, 'reserved_usd': ceiling}, ensure_ascii=False, indent=2)
    body += '\n\nAI review is advisory. Run Agent verification on this branch, inspect tests and approve manually. No automatic merge.'
    stage('pr.create')
    pr = api(f'repos/{REPO}/pulls', 'POST', {'title': f'AJAR: Issue #{issue_number}', 'head': branch, 'base': 'main', 'body': body, 'draft': True})
    print(pr['html_url'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--issue', required=True)
    args = parser.parse_args()
    try:
        run(args.issue)
    except Exception as error:
        stopped(error)
        raise SystemExit(1)

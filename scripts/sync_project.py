"""Reconcile AJAR issues/PRs and agent run summaries into a private user Project."""
import argparse
import json
import os
import re
import subprocess

OWNER = 'exgoya'
REPOS = ('ajar-core', 'ajar-template', 'ajar-practice')
TITLE = 'AJAR · 작업 추적'


def gh(*args, payload=None):
    result = subprocess.run(['gh', *args], input=None if payload is None else json.dumps(payload),
                            text=True, capture_output=True, check=True, timeout=120)
    return json.loads(result.stdout) if result.stdout.strip() else None


def gql(query, **variables):
    result = gh('api', 'graphql', '--input', '-', payload={'query': query, 'variables': variables})
    if result.get('errors'):
        raise RuntimeError('GraphQL returned errors; no response body logged')
    return result['data']


def pages(path, key=None):
    page = 1
    while True:
        result = gh('api', path + ('&' if '?' in path else '?') + f'per_page=100&page={page}')
        rows = result[key] if key else result
        yield from rows
        if len(rows) < 100:
            return
        page += 1


def project(number):
    return gql('''query($owner:String!,$number:Int!){user(login:$owner){projectV2(number:$number){
      id number title url public fields(first:100){nodes{... on ProjectV2Field{id name}
      ... on ProjectV2SingleSelectField{id name options{id name}}}}}}}''', owner=OWNER, number=number)['user']['projectV2']


def setup():
    # gh project list is owner scoped; refuse ambiguous existing matches.
    existing = gh('project', 'list', '--owner', OWNER, '--limit', '1000', '--format', 'json')['projects']
    matches = [p for p in existing if p['title'] == TITLE]
    if len(matches) > 1:
        raise ValueError('Multiple matching projects; choose a number explicitly')
    p = matches[0] if matches else gh('project', 'create', '--owner', OWNER, '--title', TITLE, '--format', 'json')
    p = project(p['number'])
    if p['public']:
        raise ValueError('Project must be private; refusing to expose private work')
    names = {f.get('name') for f in p['fields']['nodes']}
    for name in ('Agent state', 'Last run'):
        if name not in names:
            gh('project', 'field-create', str(p['number']), '--owner', OWNER,
               '--name', name, '--data-type', 'TEXT', '--format', 'json')
    for repo in REPOS:
        gh('project', 'link', str(p['number']), '--owner', OWNER, '--repo', f'{OWNER}/{repo}')
    print(json.dumps({'number': p['number'], 'url': p['url']}, ensure_ascii=False))
    return p['number']


def run_state(run):
    if run['status'] != 'completed':
        return 'Running'
    return {'success': 'Succeeded', 'failure': 'Failed', 'cancelled': 'Cancelled',
            'timed_out': 'Timed out', 'action_required': 'Needs action'}.get(run.get('conclusion'), 'Stopped')


def desired(item, run=None):
    if item.get('state') == 'closed':
        return 'Done', 'Closed'
    if run:
        return 'In Progress', run_state(run)
    if 'pull_request' in item:
        return 'In Progress', 'PR open'
    if any(x['name'] == 'agent:approved' for x in item.get('labels', [])):
        return 'Todo', 'Approved'
    return 'Todo', 'Waiting'


def sync(number):
    p = project(number)
    if not p or p['public']:
        raise ValueError('A private project is required')
    fields = {f['name']: f for f in p['fields']['nodes'] if 'name' in f}
    for name in ('Status', 'Agent state', 'Last run'):
        if name not in fields:
            raise ValueError('Missing project field; run --setup')
    options = {x['name']: x['id'] for x in fields['Status']['options']}
    if not {'Todo', 'In Progress', 'Done'} <= options.keys():
        raise ValueError('Status must include Todo, In Progress, Done')
    runs = {}
    # Latest run per issue is selected explicitly, never by branch alone.
    for run in pages(f'repos/{OWNER}/ajar-core/actions/workflows/agent-develop.yml/runs', 'workflow_runs'):
        match = re.fullmatch(r'Agent develop · Issue #([1-9][0-9]*)', run.get('display_title', ''))
        issue_number = int(match[1]) if match else {40254636624: 2}.get(run['id'])
        # One known legacy test predates issue-number run titles.
        if issue_number and issue_number not in runs:
            runs[issue_number] = run
    existing = {}
    cursor = None
    while True:
        connection = gql('''query($id:ID!,$cursor:String){node(id:$id){... on ProjectV2{
          items(first:100,after:$cursor){nodes{id content{... on Issue{id} ... on PullRequest{id}}}
          pageInfo{hasNextPage endCursor}}}}}''', id=p['id'], cursor=cursor)['node']['items']
        for item in connection['nodes']:
            if item.get('content'):
                existing[item['content']['id']] = item['id']
        if not connection['pageInfo']['hasNextPage']:
            break
        cursor = connection['pageInfo']['endCursor']
    count = 0
    for repo in REPOS:
        for item in pages(f'repos/{OWNER}/{repo}/issues?state=all'):
            node = item['node_id']
            item_id = existing.get(node)
            if not item_id:
                item_id = gql('''mutation($p:ID!,$c:ID!){addProjectV2ItemById(input:{projectId:$p,contentId:$c}){item{id}}}''',
                              p=p['id'], c=node)['addProjectV2ItemById']['item']['id']
                existing[node] = item_id
            run = runs.get(item['number']) if repo == 'ajar-core' and 'pull_request' not in item else None
            status, agent = desired(item, run)
            values = {'Status': {'singleSelectOptionId': options[status]},
                      'Agent state': {'text': agent}}
            if run:
                values['Last run'] = {'text': run['html_url']}
            for name, value in values.items():
                gql('''mutation($p:ID!,$i:ID!,$f:ID!,$v:ProjectV2FieldValue!){updateProjectV2ItemFieldValue(
                  input:{projectId:$p,itemId:$i,fieldId:$f,value:$v}){projectV2Item{id}}}''',
                    p=p['id'], i=item_id, f=fields[name]['id'], v=value)
            count += 1
    print(f'Synced {count} issues/PRs. {p["url"]}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--setup', action='store_true')
    parser.add_argument('--number', type=int, default=None)
    args = parser.parse_args()
    try:
        number = setup() if args.setup else args.number or int(os.environ['AJAR_PROJECT_NUMBER'])
        sync(number)
    except Exception as error:
        # gh may include sensitive URLs or payloads in errors; do not print them.
        print('Project sync stopped: ' + type(error).__name__)
        raise SystemExit(1)

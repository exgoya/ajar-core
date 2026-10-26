import copy
import io
from contextlib import redirect_stdout
from urllib.error import HTTPError
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import runner

ENV = dict(GITHUB_REPOSITORY=runner.REPO, GITHUB_REF='refs/heads/main', GITHUB_ACTOR='exgoya',
           AJAR_ENABLED='true', AJAR_INPUT_USD_M='1', AJAR_OUTPUT_USD_M='4', AJAR_RUN_USD='1')
FILES = [{'path': 'agent-mvp/app/greet.py', 'content': 'def greet(): return "hello"\n'},
         {'path': 'agent-mvp/app_tests/test_greet.py', 'content': 'import unittest\n'}]

class Fake:
    def __init__(self): self.calls = []; self.locked = False
    def __call__(self, path, method='GET', data=None):
        self.calls.append((path, method, data))
        if '/issues/' in path: return {'title': 'Greeting', 'body': 'Make a greeting', 'state': 'open', 'labels': [{'name': 'agent:approved'}]}
        if method == 'POST' and path.endswith('/git/refs'):
            if self.locked: raise ValueError('Already locked')
            self.locked = True
            return {}
        if '/git/ref/heads/main' in path: return {'object': {'sha': 'a'*40}}
        if method == 'GET' and '/git/commits/' in path: return {'tree': {'sha': 'b'*40}}
        if method == 'GET' and '/git/trees/' in path: return {'tree': [], 'truncated': False}
        if path.endswith('/pulls'): return {'html_url': 'https://github.com/exgoya/ajar-core/pull/99'}
        return {'sha': 'c'*40}


def models(role, context, schema):
    if role == 'developer': return {'files': copy.deepcopy(FILES)}
    if role == 'planning': return {'scope': 'greet', 'acceptance': 'works', 'risks': 'none'}
    return {'decision': 'proceed', 'reason': 'checked'}

class Tests(unittest.TestCase):
    def test_paths_and_secrets(self):
        for path in ['../x.py', '.github/workflows/x.yml', 'agent-mvp/app/../../x.py', '/app/x.py', 'agent-mvp/app/x.sh']:
            with self.subTest(path=path), self.assertRaises(ValueError):
                runner.validate_files([{'path': path, 'content': ''}, FILES[1]])
        with self.assertRaises(ValueError): runner.validate_files([FILES[0], FILES[0]])
        with self.assertRaises(ValueError): runner.validate_files([FILES[0]])
        with self.assertRaises(ValueError): runner.validate_files([{**FILES[0], 'content': 'sk-'+'A'*30}, FILES[1]])
        with self.assertRaises(ValueError): runner.validate_files([{**FILES[0], 'content': '한'*5000}, FILES[1]])
    def test_valid_files(self): self.assertEqual(runner.validate_files(FILES), FILES)
    @patch.dict(os.environ, ENV)
    def test_budget(self):
        self.assertLess(runner.reserve_cost(), 1)
        for budget in ['0.000001', '-1', 'nan', 'inf']:
            with patch.dict(os.environ, {'AJAR_RUN_USD': budget}), self.assertRaises(ValueError): runner.reserve_cost()
    @patch.dict(os.environ, ENV)
    def test_full_flow_and_no_duplicate_paid_calls(self):
        fake = Fake()
        with patch.object(runner, 'api', fake), patch.object(runner, 'model', side_effect=models) as model:
            runner.run('1')
            self.assertEqual(model.call_count, 4)
            pr = next(data for path, method, data in fake.calls if path.endswith('/pulls'))
            self.assertTrue(pr['draft'])
            with self.assertRaises(ValueError): runner.run('1')
            self.assertEqual(model.call_count, 4)
        self.assertFalse(any('/merge' in path for path, _, _ in fake.calls))
    @patch.dict(os.environ, ENV)
    def test_owner_ref_kill_switch_budget_before_writes(self):
        for setting in [{'GITHUB_ACTOR': 'stranger'}, {'GITHUB_REF': 'refs/heads/evil'}, {'AJAR_ENABLED': 'false'}, {'AJAR_RUN_USD': '0.000001'}]:
            with patch.dict(os.environ, setting), patch.object(runner, 'api') as api, self.assertRaises(ValueError): runner.run('1')
            api.assert_not_called()
    @patch.dict(os.environ, ENV)
    def test_missing_label_has_no_writes(self):
        with patch.object(runner, 'api', return_value={'state': 'open', 'labels': []}) as api, patch.object(runner, 'model') as model:
            with self.assertRaises(ValueError): runner.run('1')
            self.assertTrue(all(len(c.args) == 1 for c in api.call_args_list))
            model.assert_not_called()
    @patch.dict(os.environ, ENV)
    def test_review_rejection_and_api_failure_do_not_publish(self):
        for failure in ['review', 'planning']:
            fake = Fake()
            def generate(role, context, schema):
                if role == failure:
                    if failure == 'review': return {'decision': 'stop', 'reason': 'bug'}
                    raise TimeoutError()
                return models(role, context, schema)
            with patch.object(runner, 'api', fake), patch.object(runner, 'model', side_effect=generate):
                with self.assertRaises((ValueError, TimeoutError)): runner.run('1')
            self.assertTrue(fake.locked)
            self.assertFalse(any(path.endswith('/pulls') for path, _, _ in fake.calls))
    @patch.dict(os.environ, ENV)
    def test_existing_file_blocks_commit(self):
        fake = Fake()
        def api(path, method='GET', data=None):
            if method == 'GET' and '/git/trees/' in path: return {'tree': [{'path': FILES[0]['path']}]}
            return fake(path, method, data)
        with patch.object(runner, 'api', api), patch.object(runner, 'model', side_effect=models):
            with self.assertRaises(ValueError): runner.run('1')
        self.assertFalse(any(method == 'POST' and path.endswith('/git/commits') for path, method, _ in fake.calls))
    def test_oversized_input_never_calls_network(self):
        with patch.object(runner, 'request') as request, self.assertRaises(ValueError):
            runner.model('planning', {'issue': 'x'*25000}, runner.PLAN)
        request.assert_not_called()
    def test_request_disables_storage_and_caps_output(self):
        response = {'status': 'completed', 'output': [{'type': 'message', 'content': [{'type': 'output_text', 'text': '{"decision":"stop","reason":"scope"}'}]}]}
        with patch.dict(os.environ, {'OPENAI_MODEL': 'configured-model', 'OPENAI_API_KEY': 'fake'}), patch.object(runner, 'request', return_value=response) as request:
            runner.model('review', {'issue': 'test'}, runner.REPORT)
            payload = request.call_args.args[3]
            self.assertFalse(payload['store'])
            self.assertEqual(payload['max_output_tokens'], 3000)
            self.assertNotIn('tools', payload)


class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        runner.ATTEMPTS = runner.RESPONSES = 0

    def test_before_api_has_zero_attempts(self):
        output = io.StringIO()
        with redirect_stdout(output), patch.object(runner, 'request') as request:
            try:
                runner.model('planning', {'issue': 'x'*25000}, runner.PLAN)
            except ValueError as error:
                runner.stopped(error)
        request.assert_not_called()
        self.assertIn('stage=planning.prepare', output.getvalue())
        self.assertIn('api_attempts=0 api_responses=0', output.getvalue())
        self.assertIn('Context too large', output.getvalue())

    @patch.dict(os.environ, {'OPENAI_MODEL': 'test', 'OPENAI_API_KEY': 'fake-secret'})
    def test_http_status_without_sensitive_error_message(self):
        output = io.StringIO()
        error = HTTPError('https://example.invalid/private', 429, 'fake-secret', {}, None)
        with redirect_stdout(output), patch.object(runner, 'request', side_effect=error):
            try:
                runner.model('planning', {}, runner.PLAN)
            except HTTPError as caught:
                runner.stopped(caught)
        log = output.getvalue()
        self.assertIn('stage=planning.api_request', log)
        self.assertIn('http_status=429', log)
        self.assertIn('api_attempts=1 api_responses=0', log)
        self.assertNotIn('fake-secret', log)
        self.assertNotIn('example.invalid', log)

    @patch.dict(os.environ, {'OPENAI_MODEL': 'test', 'OPENAI_API_KEY': 'fake-secret'})
    def test_response_received_before_parse_failure_and_safe_usage(self):
        response = {'status': 'completed', 'usage': {'input_tokens': 10, 'output_tokens': 2,
                    'total_tokens': 'fake-secret'}, 'output': [{'type': 'message',
                    'content': [{'type': 'output_text', 'text': 'fake-secret invalid JSON'}]}]}
        output = io.StringIO()
        with redirect_stdout(output), patch.object(runner, 'request', return_value=response):
            try:
                runner.model('review', {}, runner.REPORT)
            except ValueError as error:
                runner.stopped(error)
        log = output.getvalue()
        self.assertIn('stage=review.parse', log)
        self.assertIn('api_attempts=1 api_responses=1', log)
        self.assertIn('"input_tokens": 10', log)
        self.assertNotIn('fake-secret', log)

    def test_unknown_exception_text_never_logged(self):
        output = io.StringIO()
        with redirect_stdout(output): runner.stopped(ValueError('fake-secret'))
        self.assertNotIn('fake-secret', output.getvalue())

if __name__ == '__main__': unittest.main()

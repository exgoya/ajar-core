import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
spec = importlib.util.spec_from_file_location('sync_project', Path(__file__).resolve().parents[1]/'scripts/sync_project.py')
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)

class ProjectTests(unittest.TestCase):
    def test_lifecycle(self):
        self.assertEqual(sync.desired({'state':'open'}), ('Todo','Waiting'))
        self.assertEqual(sync.desired({'state':'open','labels':[{'name':'agent:approved'}]}), ('Todo','Approved'))
        self.assertEqual(sync.desired({'state':'open','pull_request':{}}), ('In Progress','PR open'))
        self.assertEqual(sync.desired({'state':'closed'}, {'status':'completed','conclusion':'failure'}), ('Done','Closed'))
    def test_run_outcomes(self):
        for conclusion, label in [('failure','Failed'),('success','Succeeded'),('cancelled','Cancelled'),('timed_out','Timed out')]:
            self.assertEqual(sync.desired({'state':'open'}, {'status':'completed','conclusion':conclusion}), ('In Progress', label))
        self.assertEqual(sync.run_state({'status':'in_progress'}), 'Running')
    def test_pagination(self):
        with patch.object(sync,'gh', side_effect=[list(range(100)),[100]]) as gh:
            self.assertEqual(len(list(sync.pages('repos/exgoya/ajar-core/issues'))),101)
            self.assertIn('page=2',gh.call_args.args[-1])
    def test_public_project_has_no_writes(self):
        with patch.object(sync,'project',return_value={'public':True}), patch.object(sync,'gql') as gql:
            with self.assertRaises(ValueError): sync.sync(1)
            gql.assert_not_called()
    def test_missing_fields_has_no_writes(self):
        with patch.object(sync,'project',return_value={'public':False,'fields':{'nodes':[]}}), patch.object(sync,'gql') as gql:
            with self.assertRaises(ValueError): sync.sync(1)
            gql.assert_not_called()
    def test_reconcile_reuses_item(self):
        p={'id':'p','url':'https://example.invalid','public':False,'fields':{'nodes':[
          {'id':'s','name':'Status','options':[{'id':x,'name':x} for x in ['Todo','In Progress','Done']]},
          {'id':'a','name':'Agent state'},{'id':'l','name':'Last run'}]}}
        queries=[]
        def gql(query,**kwargs):
            queries.append(query)
            if query.startswith('query'): return {'node':{'items':{'nodes':[{'id':'existing','content':{'id':'issue'}}], 'pageInfo':{'hasNextPage':False}}}}
            return {}
        def pages(path,key=None):
            return [] if key or 'ajar-template' in path or 'ajar-practice' in path else [{'node_id':'issue','number':1,'state':'open'}]
        with patch.object(sync,'project',return_value=p), patch.object(sync,'pages',side_effect=pages), patch.object(sync,'gql',side_effect=gql):
            sync.sync(1)
        self.assertFalse(any('addProjectV2ItemById' in q for q in queries))
        self.assertEqual(sum('updateProjectV2ItemFieldValue' in q for q in queries),2)

if __name__=='__main__': unittest.main()

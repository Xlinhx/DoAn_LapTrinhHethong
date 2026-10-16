"""Regression tests for evidence truthfulness and group metadata (stdlib unittest)."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import metadata_loader as loader
from collect_evidence import parse_summary, parse_individual_tests


class PipelineTests(unittest.TestCase):
    def test_missing_summary_is_an_error(self):
        with self.assertRaises(ValueError): parse_summary('make: *** compilation failed')

    def test_empty_or_inconsistent_summary_is_an_error(self):
        for line in ('SUMMARY: 0 PASSED, 0 FAILED, 0 SKIPPED (TOTAL: 0)',
                     'SUMMARY: 2 PASSED, 0 FAILED, 0 SKIPPED (TOTAL: 3)'):
            with self.subTest(line=line), self.assertRaises(ValueError): parse_summary(line)

    def test_skip_is_not_counted_as_pass(self):
        result=parse_summary('SUMMARY: 2 PASSED, 0 FAILED, 1 SKIPPED (TOTAL: 3)')
        self.assertEqual((result['passed'],result['skipped']),(2,1))
        cases=parse_individual_tests('[PASS] Test 01: works\n[SKIP] Test 02: root\n')
        self.assertEqual([c['status'] for c in cases],['PASS','SKIP'])

    def valid_results(self):
        suite={'passed':1,'failed':0,'skipped':0,'total':1,'exit_code':0,
               'cases':[{'id':1,'status':'PASS','description':'example'}]}
        return {'source_sha256':loader.source_fingerprint(),'regular_suite':suite,
                'sanitizer_suite':copy.deepcopy(suite),'demo_run':{'exit_code':0}}

    def read_results(self,result):
        root=loader.PROJECT_ROOT/'build'; root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            path=Path(tmp)/'results.json'; path.write_text(json.dumps(result),encoding='utf8')
            with patch.object(loader,'TEST_RESULTS_PATH',path): return loader.load_test_results()

    def test_current_evidence_is_readable(self):
        self.assertEqual(self.read_results(self.valid_results())['regular_suite']['passed'],1)

    def test_stale_evidence_is_rejected(self):
        result=self.valid_results(); result['source_sha256']='old'
        with self.assertRaises(ValueError): self.read_results(result)

    def test_bad_cases_failures_and_demo_are_rejected(self):
        for kind in ('failed','duplicate_id','bad_status','demo'):
            with self.subTest(kind=kind):
                result=self.valid_results()
                if kind=='failed': result['sanitizer_suite']['exit_code']=1
                elif kind=='duplicate_id': result['regular_suite']['cases'][0]['id']=2
                elif kind=='bad_status': result['regular_suite']['cases'][0]['status']='SKIP'
                else: result['demo_run']['exit_code']=2
                with self.assertRaises(ValueError): self.read_results(result)

    def test_missing_roster_cannot_be_final(self):
        root=loader.PROJECT_ROOT/'build'; root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            path=Path(tmp)/'metadata.json'; path.write_text('{"members":[]}',encoding='utf8')
            with patch.object(loader,'METADATA_PATH',path):
                with self.assertRaises(RuntimeError): loader.load_project_metadata('final')
                self.assertEqual(loader.load_project_metadata('draft')['members'],[])

    def test_all_group_members_and_roles_survive_loading(self):
        raw={'faculty':'Faculty','instructor':'Instructor','academic_term':'Term',
             'members':[{'name':f'Member {i}','student_id':str(i),'class_name':'Class','role':'Work'} for i in range(3)]}
        root=loader.PROJECT_ROOT/'build'; root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as tmp:
            path=Path(tmp)/'metadata.json'; path.write_text(json.dumps(raw),encoding='utf8')
            with patch.object(loader,'METADATA_PATH',path):
                self.assertEqual(len(loader.load_project_metadata('final')['members']),3)
                raw['members'][1].pop('role'); path.write_text(json.dumps(raw),encoding='utf8')
                with self.assertRaises(RuntimeError): loader.load_project_metadata('final')

    def test_role_is_resolved_by_id_or_name(self):
        member={'student_id':'ID-2','name':'Member Two'}
        self.assertEqual(loader.member_role(member,[{'student_id':'ID-2','role':'Review'}]),'Review')
        self.assertEqual(loader.member_role(member,[{'member':'Member Two','role':'Tests'}]),'Tests')
        self.assertEqual(loader.member_role(member,[]),'')


if __name__=='__main__': unittest.main(verbosity=2)

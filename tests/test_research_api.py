from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
from threading import Thread
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import serve


class ResearchAPITest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),serve.Handler)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.server.server_close();cls.thread.join()

    def setUp(self):
        serve.JOBS.clear()

    def request(self,payload,headers=None):
        connection=HTTPConnection('127.0.0.1',self.server.server_port)
        connection.request('POST','/api/research',json.dumps(payload),headers or {'X-FINN-Request':'local'})
        response=connection.getresponse()
        result=response.status,json.loads(response.read());connection.close()
        return result

    def payload(self,**changes):
        return {'ticker':'HCLTECH','question':'What changed in growth guidance?','scope':'earnings','period':'latest4',**changes}

    def test_health_endpoint_does_not_call_model(self):
        connection=HTTPConnection('127.0.0.1',self.server.server_port)
        with patch.object(serve,'generate') as generate:
            connection.request('GET','/healthz')
            response=connection.getresponse()
            self.assertEqual(response.status,200)
            self.assertEqual(json.loads(response.read()),{'status':'ok'})
        connection.close();generate.assert_not_called()

    def test_server_credentials_are_not_served_as_static_files(self):
        connection=HTTPConnection('127.0.0.1',self.server.server_port)
        connection.request('GET','/.env.local')
        response=connection.getresponse();response.read();connection.close()
        self.assertEqual(response.status,404)

    def test_cross_origin_submission_is_rejected(self):
        with patch.object(serve.MODEL_POOL,'submit') as submit:
            status,_=self.request(self.payload(),{'X-FINN-Request':'local','Origin':'https://another.example'})
        self.assertEqual(status,403);submit.assert_not_called()

    def test_invalid_research_input_never_schedules_a_call(self):
        for changes in ({'ticker':'../secret'},{'question':'x'},{'scope':'news'},{'period':'../env'},{'question':[]},{'scope':[]}):
            with self.subTest(changes=changes),patch.object(serve.MODEL_POOL,'submit') as submit:
                status,_=self.request(self.payload(**changes))
                self.assertEqual(status,400);submit.assert_not_called()

    def test_duplicate_requests_share_job_but_different_questions_do_not(self):
        with patch.object(serve.MODEL_POOL,'submit') as submit:
            status,first=self.request(self.payload())
            _,duplicate=self.request(self.payload())
            _,different=self.request(self.payload(question='What changed in margins?'))
        self.assertEqual(status,202)
        self.assertEqual(first['job_id'],duplicate['job_id'])
        self.assertNotEqual(first['job_id'],different['job_id'])
        self.assertEqual(submit.call_count,2)

    def test_missing_corpus_is_reported_without_file_path(self):
        serve.JOBS['test']={'status':'queued'}
        with patch.object(serve,'generate',side_effect=FileNotFoundError('/private/path')):
            serve.run_research('test',self.payload())
        self.assertEqual(serve.JOBS['test']['status'],'failed')
        self.assertNotIn('/private',serve.JOBS['test']['error'])

    def test_background_result_preserves_checked_evidence(self):
        serve.JOBS['test']={'status':'queued'}
        expected={'status':'evidence_checked_draft','observations':[{'quote':'exact source words','source':{'pdf_page':12}}]}
        with patch.object(serve,'generate',return_value=expected) as generate:
            serve.run_research('test',self.payload())
        self.assertEqual(serve.JOBS['test']['status'],'complete')
        self.assertEqual(serve.JOBS['test']['result'],expected)
        generate.assert_called_once_with(**self.payload())


if __name__=='__main__':
    unittest.main()

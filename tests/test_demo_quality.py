import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from model_research import retrieve
from refresh_announcements import classify,match_issuer


class DemoQualityTest(unittest.TestCase):
    def test_annual_report_wrapper_does_not_select_cover_page(self):
        corpus={'documents':[{'id':'ar','title':'Annual report','url':'https://issuer.example/ar.pdf'}],'passages':[
            {'document':'ar','page':2,'event_type':'annual_report','text':'Growth with Discipline ANNUAL REPORT'},
            {'document':'ar','page':163,'event_type':'annual_report','text':'Net working capital turnover ratio is disclosed alongside trade receivables and payables.'}]}
        result=retrieve(corpus,'What does the annual report say about working capital?','annual')
        self.assertEqual(result[0]['pdf_page'],163)
        self.assertIn('working capital',result[0]['text'])

    def test_generic_document_question_does_not_invent_topic_evidence(self):
        corpus={'documents':[],'passages':[]}
        self.assertEqual(retrieve(corpus,'What does the annual report say?','annual'),[])

    def test_recording_of_results_is_not_an_actual_results_release(self):
        self.assertEqual(classify('Audio recording of the financial results earnings call'),('earnings_call',50))
        self.assertEqual(classify('Unaudited quarterly financial results'),('results',90))

    def test_actual_exchange_description_calibration_set(self):
        for case in json.loads((ROOT/'data/announcement_eval.json').read_text())['cases']:
            with self.subTest(issuer=case['issuer']):
                self.assertEqual(classify(case['description'])[0],case['expected_category'])

    def test_similarly_named_issuers_do_not_enter_portfolio(self):
        for issuer in ['Slone Infosystems Limited','Reliance Mutual Fund','HDFC Asset Management Company Limited']:
            self.assertIsNone(match_issuer(issuer,'General Updates',{'INFY','RELIANCE','HDFCBANK'}))


if __name__=='__main__':
    unittest.main()

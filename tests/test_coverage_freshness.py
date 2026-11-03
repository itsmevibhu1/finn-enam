from datetime import datetime,timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from source_metadata import transcript_metadata,quarter_coverage
from market_freshness import freshness,expected_session
from research_pipeline import issuer_host_evidence,retain_collection,download
from refresh_market import chart_rows


class CoverageTest(unittest.TestCase):
    def test_earnings_call_later_in_combined_pdf_is_found(self):
        pages=[{'pdf_page':i,'text':''} for i in range(1,31)]
        pages[0]['text']='TO ALL STOCK EXCHANGES. Sub: Transcripts of earnings call'
        pages[1]['text']='Example Limited\nMedia Conference Call\nCORPORATE PARTICIPANTS'
        pages[23]['text']='Example Limited\nQ2 FY27 Earnings Conference Call\nCORPORATE PARTICIPANTS'
        result=transcript_metadata(pages)
        self.assertEqual(result['event_type'],'mixed_transcripts')
        self.assertEqual(result['earnings_periods'],['Q2 FY2027'])
        earnings=next(s for s in result['sections'] if s['event_type']=='earnings_call')
        self.assertEqual((earnings['start_page'],earnings['end_page']),(24,30))

    def test_analyst_meet_does_not_fill_earnings_quarter(self):
        result=transcript_metadata([{'text':'Astral Analyst Meet, 2026\n20th May 2026\nQ4 FY26 discussed'}])
        self.assertEqual(result['earnings_periods'],[])
        self.assertEqual(result['event_type'],'investor_event')

    def test_four_distinct_quarters_can_still_have_a_gap(self):
        result=quarter_coverage(['Q2 FY2027','Q4 FY2026','Q3 FY2026','Q2 FY2026'])
        self.assertFalse(result['complete'])
        self.assertEqual(result['missing'],['Q1 FY2027'])

    def test_duplicate_quarters_do_not_count_twice(self):
        result=quarter_coverage(['Q2 FY2027','Q2 FY2027','Q1 FY2027','Q4 FY2026'])
        self.assertFalse(result['complete'])

    def test_failed_refresh_preserves_last_usable_registry(self):
        registry={'companies':{'TEST':{'status':'ok','documents':[{'id':'retained'}]}}}
        retain_collection(registry,'TEST',{'status':'failed','documents':[],'error':'DNS failed'})
        self.assertEqual(registry['companies']['TEST']['documents'],[{'id':'retained'}])
        self.assertEqual(registry['companies']['TEST']['last_collection_attempt']['error'],'DNS failed')

    def test_issuer_domain_requires_a_labelled_website_statement(self):
        with tempfile.TemporaryDirectory() as directory:
            pages=[{'pdf_page':1,'text':'Annual report. Website of the Company at: https://www.issuer.example/investors/. Other link: https://vendor.example/report.'}]
            (Path(directory)/'pages.json').write_text(json.dumps(pages))
            result=issuer_host_evidence({'directory':directory,'url':'https://www.bseindia.com/report.pdf'})
            self.assertEqual([r['host'] for r in result],['issuer.example'])
            self.assertEqual(result[0]['pdf_page'],1)

    def test_same_pdf_at_second_primary_url_is_an_alias(self):
        content=b'%PDF-1.4\npreviously validated fixture'
        digest=hashlib.sha256(content).hexdigest()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            destination=root/'data/documents/TEST/transcript'/digest
            destination.mkdir(parents=True)
            (destination/'original.pdf').write_bytes(content)
            (destination/'manifest.json').write_text(json.dumps({'source_url':'https://issuer.example/original.pdf'}))
            response=io.BytesIO(content)
            response.url='https://issuer.example/mirror.pdf'
            with patch('research_pipeline.ROOT',root),patch('research_pipeline.urlopen',return_value=response):
                result=download({'ticker':'TEST','kind':'transcript','period':'Q1 FY2027','url':response.url,'website_host':'issuer.example'})
            self.assertEqual(result['status'],'already_imported')
            self.assertEqual(result['source_alias_of'],'https://issuer.example/original.pdf')


class FreshnessTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.calendar=json.loads((ROOT/'config/nse_calendar.json').read_text())

    def test_before_close_expects_previous_completed_session(self):
        now=datetime(2026,11,3,3,tzinfo=timezone.utc)
        self.assertEqual(expected_session(now,self.calendar),'2026-11-02')

    def test_weekend_is_skipped(self):
        now=datetime(2026,11,2,3,tzinfo=timezone.utc)
        self.assertEqual(expected_session(now,self.calendar),'2026-10-30')

    def test_exchange_holiday_is_skipped(self):
        now=datetime(2026,11,10,12,tzinfo=timezone.utc)
        self.assertEqual(expected_session(now,self.calendar),'2026-11-09')

    def test_special_sunday_session_is_not_lost(self):
        now=datetime(2026,11,9,3,tzinfo=timezone.utc)
        self.assertEqual(expected_session(now,self.calendar),'2026-11-08')

    def test_unknown_calendar_year_is_not_assumed_current(self):
        now=datetime(2027,2,2,12,tzinfo=timezone.utc)
        self.assertEqual(freshness('2027-02-02',now,self.calendar)['status'],'unknown_calendar')

    def test_http_success_does_not_imply_freshness(self):
        now=datetime(2026,11,3,3,tzinfo=timezone.utc)
        self.assertEqual(freshness('2026-10-30',now,self.calendar)['status'],'stale')
        self.assertEqual(freshness('2026-11-02',now,self.calendar)['status'],'current')

    def test_future_or_incomplete_provider_session_is_not_current(self):
        now=datetime(2026,11,3,3,tzinfo=timezone.utc)
        self.assertEqual(freshness('2026-11-03',now,self.calendar)['status'],'unexpected_session')

    def test_invalid_and_future_rows_are_excluded(self):
        now=datetime(2026,11,3,3,tzinfo=timezone.utc)
        stamps=[int(datetime(2026,11,d,3,tzinfo=timezone.utc).timestamp()) for d in (1,2,3,4)]
        payload={'chart':{'result':[{'timestamp':stamps,'indicators':{'quote':[{'close':[float('nan'),100,101,102],'volume':[1,100,100,100]}]},'meta':{'currency':'INR'}}]}}
        rows,currency=chart_rows(payload,now)
        self.assertEqual([r['date'] for r in rows],['2026-11-02'])
        self.assertEqual(currency,'INR')


if __name__=='__main__':
    unittest.main()

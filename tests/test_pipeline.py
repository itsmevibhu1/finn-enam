from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
from threading import Thread
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from research_pipeline import DirectoryParser, safe_primary, document_quality
from refresh_announcements import parse_timestamp, classify
from build_corpus import transcript_metadata, chunks
from serve import Handler


class SourcePipelineTest(unittest.TestCase):
    def test_nse_non_rfc_date_format(self):
        parsed=parse_timestamp('30-OCT-2026 20:28')
        self.assertEqual(parsed.isoformat(),'2026-10-30T20:28:00+05:30')

    def test_nse_invalid_date_is_skipped(self):
        self.assertIsNone(parse_timestamp('invalid'))

    def test_results_newspaper_is_routine(self):
        self.assertEqual(classify('Newspaper publication of financial results'),('routine',5))

    def test_directory_parser_preserves_source_section(self):
        parser=DirectoryParser()
        parser.feed('<h1>Example Ltd</h1><h3>Annual reports</h3><a href="https://www.bseindia.com/a.pdf">Annual Report 2026</a><h3>Concalls</h3>Oct 2026<a href="https://example.com/c.pdf">Transcript</a>')
        self.assertEqual(parser.name,'Example Ltd')
        self.assertEqual(parser.links[0]['section'],'annual reports')
        self.assertEqual(parser.links[1]['section'],'concalls')
        self.assertIn('Oct 2026',parser.links[1]['context'])

    def test_source_domain_boundary(self):
        self.assertTrue(safe_primary('https://nsearchives.nseindia.com/a.pdf','example.com'))
        self.assertTrue(safe_primary('https://investor.example.com/a.pdf','example.com'))
        self.assertFalse(safe_primary('https://example.com.evil.invalid/a.pdf','example.com'))
        self.assertFalse(safe_primary('http://example.com/a.pdf','example.com'))
        self.assertFalse(safe_primary('https://user:secret@example.com/a.pdf','example.com'))

    def test_audio_notice_is_not_a_transcript(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/'pages.json').write_text(json.dumps([{'pdf_page':1,'text':'Astral Limited. Audio recording of earnings call is available at the link.'}]))
            result=document_quality({'status':'imported','directory':directory,'kind':'transcript'},'Astral Ltd')
            self.assertFalse(result['usable'])
            self.assertIn('audio',result['reason'])

    def test_investor_event_does_not_become_a_quarterly_call(self):
        result=transcript_metadata([{'text':'Investor AI Day 2026, February 17, 2026. Q3 FY26 performance discussed.'}])
        self.assertEqual(result['event_type'],'investor_event')
        self.assertIsNone(result['reporting_period'])

    def test_media_conference_does_not_inherit_a_quarter(self):
        result=transcript_metadata([{'text':'Infosys Limited Media Conference Call October 23, 2026'}])
        self.assertEqual(result['event_type'],'media_conference')
        self.assertIsNone(result['reporting_period'])

    def test_fiscal_quarter_from_primary_statement(self):
        result=transcript_metadata([{'text':'Financial results for the quarter ended September 30, 2026'}])
        self.assertEqual(result['reporting_period'],'Q2 FY2027')

    def test_chunking_terminates_and_covers_source_end(self):
        text=' '.join(f'word{i}' for i in range(1000))
        parts=list(chunks(text,limit=100,overlap=15))
        self.assertGreater(len(parts),1)
        self.assertTrue(parts[-1].endswith('word999'))
        self.assertTrue(all(len(p)<=100 for p in parts))


class LocalAPIInputTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
        cls.thread=Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def request(self,payload,headers=None):
        connection=HTTPConnection('127.0.0.1',self.server.server_port)
        connection.request('POST','/api/collect',body=json.dumps(payload),headers=headers or {})
        response=connection.getresponse()
        result=response.status,json.loads(response.read())
        connection.close()
        return result

    def test_cross_site_job_submission_rejected(self):
        status,_=self.request({'ticker':'INFY'})
        self.assertEqual(status,403)

    def test_path_traversal_ticker_rejected(self):
        status,_=self.request({'ticker':'../secret'},{'X-FINN-Request':'local'})
        self.assertEqual(status,400)

    def test_non_object_body_rejected(self):
        status,_=self.request([] ,{'X-FINN-Request':'local'})
        self.assertEqual(status,400)


if __name__=='__main__':
    unittest.main()

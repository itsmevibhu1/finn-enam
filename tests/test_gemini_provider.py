import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError,URLError

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import gemini_provider as provider
from model_research import validate_draft


class GeminiProviderTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.root_patch=patch.object(provider,'ROOT',self.root)
        self.root_patch.start()
        self.env_patch=patch.dict(os.environ,{},clear=True)
        self.env_patch.start()

    def tearDown(self):
        self.env_patch.stop();self.root_patch.stop();self.temp.cleanup()

    def configure(self,**changes):
        values={'GEMINI_API_KEY':'test-secret-never-log','GEMINI_MODEL':'gemini-3.5-flash-lite',**changes}
        (self.root/'.env.local').write_text('\n'.join(f'{k}={v}' for k,v in values.items()))

    def test_missing_key_fails_before_any_network_call(self):
        with patch.object(provider,'urlopen') as request:
            with self.assertRaisesRegex(ValueError,'GEMINI_API_KEY'):
                provider.complete([{'role':'user','content':'test'}],{})
            request.assert_not_called()

    def test_key_is_not_exposed_in_settings_repr(self):
        self.configure()
        self.assertNotIn('test-secret',repr(provider.settings()))

    def test_environment_overrides_file_without_shell_evaluation(self):
        self.configure()
        with (self.root/'.env.local').open('a') as handle:
            handle.write('\nUNRELATED=$(echo unsafe)\n')
        os.environ['GEMINI_MODEL']='gemini-3.5-flash-lite'
        self.assertNotIn('UNRELATED',provider.configuration())

    def test_paid_only_model_is_rejected(self):
        self.configure(GEMINI_MODEL='gemini-4-argon')
        with self.assertRaisesRegex(ValueError,'paid-model fallback'):
            provider.settings()

    def test_request_cap_blocks_an_additional_attempt(self):
        config=provider.Settings('not-a-live-key',daily_limit=2)
        provider.reserve_request(config)
        provider.reserve_request(config)
        with self.assertRaisesRegex(ValueError,'daily Gemini request cap'):
            provider.reserve_request(config)

    def test_key_uses_header_not_url_and_schema_is_requested(self):
        self.configure()
        response=io.BytesIO(json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{"answerable":false}'}]}}],'usageMetadata':{'totalTokenCount':10}}).encode())
        with patch.object(provider,'urlopen',return_value=response) as request:
            result=provider.complete([{'role':'system','content':'instructions'},{'role':'user','content':'public evidence'}],{'type':'object'})
        sent=request.call_args.args[0]
        self.assertNotIn('test-secret',sent.full_url)
        self.assertEqual(sent.get_header('X-goog-api-key'),'test-secret-never-log')
        self.assertEqual(json.loads(sent.data)['generationConfig']['responseMimeType'],'application/json')
        self.assertIn('answerable',result['choices'][0]['message']['content'])

    def test_rate_limit_stops_without_paid_fallback_or_secret_leak(self):
        self.configure()
        error=HTTPError('https://generativelanguage.googleapis.com',429,'quota',{},io.BytesIO(b'test-secret-never-log'))
        with patch.object(provider,'urlopen',side_effect=error) as request:
            with self.assertRaisesRegex(ValueError,'no paid fallback') as raised:
                provider.complete([{'role':'user','content':'test'}],{})
        self.assertNotIn('test-secret',str(raised.exception))
        self.assertEqual(request.call_count,1)

    def test_network_failure_is_sanitized_and_not_retried(self):
        self.configure()
        for error in (URLError('test-secret-never-log'),TimeoutError('test-secret-never-log')):
            with self.subTest(error=type(error).__name__):
                with patch.object(provider,'urlopen',side_effect=error) as request:
                    with self.assertRaisesRegex(ValueError,'Authentication is unverified') as raised:
                        provider.complete([{'role':'user','content':'test'}],{})
                self.assertNotIn('test-secret',str(raised.exception))
                self.assertEqual(request.call_count,1)

    def test_temporary_overload_retries_once_and_counts_both_attempts(self):
        self.configure()
        error=HTTPError('https://generativelanguage.googleapis.com',503,'busy',{},io.BytesIO(b'test-secret-never-log'))
        response=io.BytesIO(json.dumps({'candidates':[{'finishReason':'STOP','content':{'parts':[{'text':'{}'}]}}]}).encode())
        with patch.object(provider,'urlopen',side_effect=[error,response]) as request,patch.object(provider.time,'sleep') as sleep:
            provider.complete([{'role':'user','content':'public evidence'}],{})
        self.assertEqual(request.call_count,2)
        sleep.assert_called_once_with(2)
        self.assertEqual(json.loads((self.root/'data/model_cache/gemini_usage.json').read_text())['attempts'],2)

    def test_repeated_overload_stops_after_one_retry(self):
        self.configure()
        errors=[HTTPError('https://generativelanguage.googleapis.com',503,'busy',{},io.BytesIO()) for _ in range(2)]
        with patch.object(provider,'urlopen',side_effect=errors) as request,patch.object(provider.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'temporarily busy'):
                provider.complete([{'role':'user','content':'public evidence'}],{})
        self.assertEqual(request.call_count,2)

    def test_retry_cannot_bypass_daily_cap(self):
        self.configure(FINN_GEMINI_DAILY_REQUEST_LIMIT='1')
        error=HTTPError('https://generativelanguage.googleapis.com',503,'busy',{},io.BytesIO())
        with patch.object(provider,'urlopen',side_effect=error) as request,patch.object(provider.time,'sleep'):
            with self.assertRaisesRegex(ValueError,'daily Gemini request cap'):
                provider.complete([{'role':'user','content':'public evidence'}],{})
        self.assertEqual(request.call_count,1)


class EvidenceValidationTest(unittest.TestCase):
    def setUp(self):
        self.evidence=[{'source_id':'E1','document_id':'source-document','text':'Management retained its operating margin guidance for the fiscal year.','url':'https://company.example/report.pdf','pdf_page':3}]
        self.draft={'answerable':True,'headline':'Margin outlook remains unchanged','observations':[{'source_id':'E1','quote':'Management retained its operating margin guidance','interpretation':'Management maintained its stated profitability outlook.'}],'next_question':'What evidence would establish delivery against this outlook?'}

    def test_exact_primary_quote_keeps_source_page(self):
        answer=validate_draft(self.draft,self.evidence)
        self.assertEqual(answer['observations'][0]['source']['pdf_page'],3)

    def test_invented_quote_is_rejected(self):
        self.draft['observations'][0]['quote']='Revenue has doubled this year'
        with self.assertRaisesRegex(ValueError,'match the supplied passage'):
            validate_draft(self.draft,self.evidence)

    def test_unknown_citation_is_rejected(self):
        self.draft['observations'][0]['source_id']='E99'
        with self.assertRaisesRegex(ValueError,'unknown source'):
            validate_draft(self.draft,self.evidence)

    def test_model_numerical_interpretation_is_rejected(self):
        self.draft['observations'][0]['interpretation']='Margins should rise 20%.'
        with self.assertRaisesRegex(ValueError,'no numerical claims'):
            validate_draft(self.draft,self.evidence)


if __name__=='__main__':
    unittest.main()

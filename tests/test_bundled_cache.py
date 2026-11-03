import copy
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import model_research as research


class BundledCacheTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.static=self.root/'static'
        (self.static/'corpora').mkdir(parents=True)
        (self.root/'data').mkdir()
        self.original=research.static_directory()
        (self.static/'snapshot.json').write_bytes((self.original/'snapshot.json').read_bytes())
        (self.root/'data/demo_answers.json').write_bytes((ROOT/'data/demo_answers.json').read_bytes())
        self.bundle=json.loads((self.root/'data/demo_answers.json').read_text())
        for answer in self.bundle.values():
            name=f'{answer["ticker"]}.json'
            (self.static/'corpora'/name).write_bytes((self.original/'corpora'/name).read_bytes())

    def tearDown(self):
        self.temp.cleanup()

    def generate(self,answer):
        with patch.object(research,'ROOT',self.root),patch.object(research,'static_directory',return_value=self.static),patch.object(research,'configuration',return_value={'FINN_AI_PROVIDER':'gemini'}),patch.object(research,'gemini_settings',return_value=SimpleNamespace(model='gemini-3.5-flash-lite')),patch.object(research,'gemini_complete',side_effect=RuntimeError('Model call attempted')):
            return research.generate(answer['ticker'],answer['question'],answer['scope'],answer['period'])

    def test_recorded_demos_work_after_restart_without_model_calls(self):
        for answer in self.bundle.values():
            result=self.generate(answer)
            self.assertTrue(result['cache_hit'])
            self.assertEqual(result['cache_source'],'bundled_verified_demo')

    def test_changed_corpus_cannot_reuse_an_old_bundled_answer(self):
        answer=next(iter(self.bundle.values()))
        path=self.static/'corpora'/f'{answer["ticker"]}.json'
        path.write_bytes(path.read_bytes()+b' ')
        with self.assertRaisesRegex(RuntimeError,'Model call attempted'):
            self.generate(answer)

    def test_source_metadata_is_rebuilt_from_the_corpus(self):
        answer=copy.deepcopy(next(iter(self.bundle.values())))
        answer['observations'][0]['source']['url']='https://wrong.example/fake.pdf'
        corpus=json.loads((self.static/'corpora'/f'{answer["ticker"]}.json').read_text())
        checked=research.check_bundled_answer(answer,corpus)
        self.assertNotIn('wrong.example',checked['observations'][0]['source']['url'])


if __name__=='__main__':
    unittest.main()

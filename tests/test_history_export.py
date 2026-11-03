from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from export_build_history import sanitize,visible_messages


class HistoryExportTest(unittest.TestCase):
    def test_known_key_and_selected_fragment_are_redacted(self):
        secret='example-secret-key-never-publish'
        text='## Active file: .env.local\n## Active selection of the file:\nselected-sensitive-fragment\n## Open tabs:\n.env.local\n## My request:\nkey saved '+secret
        cleaned=sanitize(text,[secret])
        self.assertNotIn(secret,cleaned)
        self.assertNotIn('selected-sensitive-fragment',cleaned)
        self.assertIn('key saved',cleaned)

    def test_only_visible_user_and_assistant_messages_are_exported(self):
        def record(role,phase,text):
            return {'type':'response_item','payload':{'type':'message','role':role,'phase':phase,'content':[{'type':'text','text':text}]}}
        records=[record('developer',None,'private instruction'),record('user',None,'user request'),record('assistant','analysis','private reasoning'),record('assistant','commentary','progress'),record('assistant','final_answer','answer'),{'type':'response_item','payload':{'type':'function_call_output','output':'credential'}}]
        self.assertEqual([m['text'] for m in visible_messages(records)],['user request','progress','answer'])

    def test_credential_assignment_is_redacted(self):
        self.assertNotIn('long-sensitive-value',sanitize('GEMINI_API_KEY=long-sensitive-value'))


if __name__=='__main__':
    unittest.main()

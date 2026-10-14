import unittest,os,json
from unittest.mock import patch,MagicMock
import app
class LocalTutor(unittest.TestCase):
    @patch.dict(os.environ,{"AI_PROVIDER":"ollama","OPENAI_API_KEY":"unused"})
    @patch("urllib.request.urlopen")
    def test_local(self,urlopen):
        response=MagicMock()
        response.read.return_value=json.dumps({"message":{"content":"Uma lista guarda valores."}}).encode()
        urlopen.return_value.__enter__.return_value=response
        r=app.app.test_client().post('/api/tutor',json={"pergunta":"Listas?"})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json["title"],"Tutora IA local")
        req=urlopen.call_args.args[0]
        self.assertEqual(req.full_url,"http://127.0.0.1:11434/api/chat")
        self.assertNotIn("Authorization",req.headers)
    @patch.dict(os.environ,{"AI_PROVIDER":"ollama"})
    @patch("urllib.request.urlopen")
    def test_offline(self,urlopen):
        import urllib.error
        urlopen.side_effect=urllib.error.URLError("offline")
        r=app.app.test_client().post('/api/tutor',json={"pergunta":"Listas?"})
        self.assertEqual(r.status_code,503)
        self.assertIn("ollama serve",r.json["error"])
if __name__=="__main__":unittest.main()

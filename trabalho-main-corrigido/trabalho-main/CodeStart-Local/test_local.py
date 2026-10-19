import os, re, json, tempfile, unittest
from unittest.mock import patch, MagicMock
os.environ["APP_DATA_DIR"] = tempfile.mkdtemp()
import app


def client():
    c = app.app.test_client()
    html = c.get("/").get_data(as_text=True)
    c.csrf = {"X-CSRF-Token": re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)}
    return c


class LocalTutor(unittest.TestCase):
    @patch.dict(os.environ, {"AI_PROVIDER": "ollama", "OPENAI_API_KEY": "unused"})
    @patch("urllib.request.urlopen")
    def test_local(self, urlopen):
        response = MagicMock()
        response.read.return_value = json.dumps({"message": {"content": "Uma lista guarda valores."}}).encode()
        urlopen.return_value.__enter__.return_value = response
        c = client()
        r = c.post('/api/tutor', json={"pergunta": "Listas?"}, headers=c.csrf)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["title"], "Tutora IA local")
        req = urlopen.call_args.args[0]
        self.assertEqual(req.full_url, "http://127.0.0.1:11434/api/chat")
        self.assertNotIn("Authorization", req.headers)

    @patch.dict(os.environ, {"AI_PROVIDER": "ollama", "TUTOR_FALLBACK": "0"})
    @patch("urllib.request.urlopen")
    def test_offline_without_fallback(self, urlopen):
        import urllib.error
        urlopen.side_effect = urllib.error.URLError("offline")
        c = client()
        r = c.post('/api/tutor', json={"pergunta": "Listas?"}, headers=c.csrf)
        self.assertEqual(r.status_code, 503)
        self.assertIn("ollama serve", r.json["error"])

    @patch.dict(os.environ, {"AI_PROVIDER": "ollama"})
    @patch("urllib.request.urlopen")
    def test_offline_falls_back_to_material(self, urlopen):
        import urllib.error
        urlopen.side_effect = urllib.error.URLError("offline")
        c = client()
        r = c.post('/api/tutor', json={"pergunta": "Listas em Python"}, headers=c.csrf)
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json["success"])


if __name__ == "__main__":
    unittest.main()

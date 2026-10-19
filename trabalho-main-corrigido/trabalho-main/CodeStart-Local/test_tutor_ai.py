import os, re, tempfile, unittest
from unittest.mock import patch, MagicMock
os.environ["APP_DATA_DIR"] = tempfile.mkdtemp()
import app as module


def client():
    c = module.app.test_client()
    html = c.get("/").get_data(as_text=True)
    c.csrf = {"X-CSRF-Token": re.search(r'name="csrf-token" content="([^"]+)"', html).group(1)}
    return c


class TutorAI(unittest.TestCase):
    def setUp(self):
        self.client = client()
        module._tutor_calls.clear()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-only", "AI_PROVIDER": "openai"})
    @patch("openai.OpenAI")
    def test_ai_history_and_privacy(self, sdk):
        sdk.return_value.__enter__.return_value.responses.create.return_value.output_text = "Uma lista guarda elementos."
        r = self.client.post("/api/tutor", headers=self.client.csrf,
                             json={"pergunta": "Explique listas", "historico": [{"q": "Python", "text": "Vamos estudar."}]})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json["mode"], "ai")
        args = sdk.return_value.__enter__.return_value.responses.create.call_args.kwargs
        self.assertFalse(args["store"])
        self.assertEqual(len(args["input"]), 3)

    @patch.dict(os.environ, {"GROQ_API_KEY": "test-only", "AI_PROVIDER": "auto"})
    @patch("openai.OpenAI")
    def test_auto_uses_groq_when_key_present(self, sdk):
        create = sdk.return_value.__enter__.return_value.chat.completions.create
        create.return_value.choices = [MagicMock(message=MagicMock(content="Resposta da IA."))]
        r = self.client.post("/api/tutor", headers=self.client.csrf, json={"pergunta": "O que é Flask?"})
        self.assertEqual(r.json["mode"], "ai")
        self.assertIn("groq.com", sdk.call_args.kwargs["base_url"])

    @patch.dict(os.environ, {"AI_PROVIDER": "auto", "GROQ_API_KEY": ""})
    def test_auto_without_key_answers_from_material(self):
        r = self.client.post("/api/tutor", headers=self.client.csrf, json={"pergunta": "Como funcionam as listas em Python?"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json["success"])
        self.assertNotEqual(r.json.get("mode"), "ai")

    def test_invalid_input(self):
        for payload in [{"pergunta": 123}, {"pergunta": "a" * 2001}, {"pergunta": "Oi", "historico": {}}]:
            self.assertEqual(self.client.post("/api/tutor", json=payload, headers=self.client.csrf).status_code, 400)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-only", "AI_PROVIDER": "openai"})
    @patch("openai.OpenAI")
    def test_budget_falls_back_without_calling_api(self, sdk):
        module._tutor_calls.extend([module.time.monotonic()] * 100)
        r = self.client.post("/api/tutor", headers=self.client.csrf, json={"pergunta": "Python"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("A IA está indisponível", r.json["answer"])
        sdk.assert_not_called()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-only", "AI_PROVIDER": "openai"})
    @patch("openai.OpenAI")
    def test_connection_failure_falls_back(self, sdk):
        import openai
        sdk.return_value.__enter__.return_value.responses.create.side_effect = openai.APIConnectionError(request=MagicMock())
        r = self.client.post("/api/tutor", headers=self.client.csrf, json={"pergunta": "Python"})
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json["success"])

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-only", "AI_PROVIDER": "openai", "TUTOR_FALLBACK": "0"})
    @patch("openai.OpenAI")
    def test_connection_failure_without_fallback(self, sdk):
        import openai
        sdk.return_value.__enter__.return_value.responses.create.side_effect = openai.APIConnectionError(request=MagicMock())
        self.assertEqual(self.client.post("/api/tutor", headers=self.client.csrf, json={"pergunta": "Python"}).status_code, 504)


if __name__ == "__main__":
    unittest.main()

import os
import unittest
from unittest.mock import patch, MagicMock
import app as module
class TutorAI(unittest.TestCase):
    def setUp(self):
        self.client=module.app.test_client()
        module._tutor_calls.clear()
    @patch.dict(os.environ, {"OPENAI_API_KEY":"test-only", "AI_PROVIDER":"openai"})
    @patch("openai.OpenAI")
    def test_ai_history_and_privacy(self, sdk):
        sdk.return_value.__enter__.return_value.responses.create.return_value.output_text="Uma lista guarda elementos."
        r=self.client.post("/api/tutor",json={"pergunta":"Explique listas","historico":[{"q":"Python","text":"Vamos estudar."}]})
        self.assertEqual(r.status_code,200)
        self.assertEqual(r.json["mode"],"ai")
        args=sdk.return_value.__enter__.return_value.responses.create.call_args.kwargs
        self.assertFalse(args["store"])
        self.assertEqual(len(args["input"]),3)
    def test_invalid_input(self):
        for payload in [{"pergunta":123},{"pergunta":"a"*2001},{"pergunta":"Oi","historico":{}}]:
            self.assertEqual(self.client.post("/api/tutor",json=payload).status_code,400)
    @patch.dict(os.environ, {"OPENAI_API_KEY":"test-only", "AI_PROVIDER":"openai"})
    @patch("openai.OpenAI")
    def test_budget(self,sdk):
        module._tutor_calls.extend([module.time.monotonic()]*100)
        self.assertEqual(self.client.post("/api/tutor",json={"pergunta":"Python"}).status_code,429)
        sdk.assert_not_called()
    @patch.dict(os.environ, {"OPENAI_API_KEY":"test-only", "AI_PROVIDER":"openai"})
    @patch("openai.OpenAI")
    def test_connection_failure(self,sdk):
        import openai
        sdk.return_value.__enter__.return_value.responses.create.side_effect=openai.APIConnectionError(request=MagicMock())
        self.assertEqual(self.client.post("/api/tutor",json={"pergunta":"Python"}).status_code,504)
if __name__=="__main__":
    unittest.main()

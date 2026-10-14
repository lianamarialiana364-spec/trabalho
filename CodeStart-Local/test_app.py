import os
os.environ["AI_PROVIDER"] = "local"
import unittest
from app import app, load_curriculum

class CodeStartTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_template_and_assets(self):
        for path in ['/', '/static/upgrade.js', '/static/upgrade.css']:
            with self.client.get(path) as response:
                self.assertEqual(response.status_code, 200)

    def test_complete_catalog(self):
        data = self.client.get('/api/catalogo').get_json()
        self.assertEqual(data['course_count'], 11)
        self.assertEqual(data['lesson_count'], 639)
        self.assertEqual(len(data['projects']), 12)

    def test_combined_trail_no_duplicates(self):
        result = self.client.post('/api/trilha', json={'objetivos':['python','java']}).get_json()
        self.assertTrue(result['success'])
        self.assertEqual(len(result['course_ids']),len(set(result['course_ids'])))

    def test_bad_payloads(self):
        for payload in [[], 'texto', 12]:
            self.assertEqual(self.client.post('/api/trilha', json=payload).status_code, 400)

    def test_python_imports_and_error(self):
        result = self.client.post('/api/editor/python/check', json={'code':'from flask import Flask\nimport os, json'}).get_json()
        self.assertEqual(result['imports'], ['flask','os','json'])
        result = self.client.post('/api/editor/python/check', json={'code':'def oi('}).get_json()
        self.assertFalse(result['valid'])

    def test_java_strings_comments_and_main(self):
        code = 'public class Main { public static void main(String[] args) { System.out.println("https://exemplo.com/{"); } }'
        result = self.client.post('/api/editor/java/check', json={'code':code}).get_json()
        self.assertTrue(result['valid'])
        self.assertTrue(result['has_main'])
        result = self.client.post('/api/editor/java/check', json={'code':'public class Main { ('}).get_json()
        self.assertFalse(result['valid'])

    def test_sql_readonly(self):
        result = self.client.post('/api/editor/sql', json={'query':'SELECT * FROM usuarios WHERE ativo = 1'}).get_json()
        self.assertEqual(result['count'], 3)
        for query in ['DELETE FROM usuarios', 'WITH ids AS (SELECT 1) DELETE FROM usuarios']:
            self.assertEqual(self.client.post('/api/editor/sql', json={'query':query}).status_code,400)

    def test_sql_timeout(self):
        query = 'WITH RECURSIVE x(n) AS (SELECT 1 UNION ALL SELECT n+1 FROM x) SELECT sum(n) FROM x'
        self.assertEqual(self.client.post('/api/editor/sql', json={'query':query}).status_code,400)

    def test_json_valid_and_invalid(self):
        for code,valid in [('{"a":1}',True),('{',False)]:
            self.assertEqual(self.client.post('/api/editor/json/check',json={'code':code}).get_json()['valid'],valid)

    def test_tutor(self):
        self.assertEqual(self.client.post('/api/tutor',json={'pergunta':''}).status_code,400)
        result = self.client.post('/api/tutor',json={'pergunta':'listas Python'}).get_json()
        self.assertTrue(result['success'])
        self.assertTrue(result['answer'])

if __name__ == '__main__':
    unittest.main()

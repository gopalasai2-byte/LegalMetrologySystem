import os
import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import app
from database import init_db

class TestFlaskRoutes(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        app.config['TESTING'] = True
        init_db()

    def setUp(self):
        self.client = app.test_client()

    def test_homepage(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Legal Metrology Compliance System", response.data)
        self.assertIn(b"Total Audits", response.data)

    def test_check_page(self):
        response = self.client.get('/check')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Upload Product Label", response.data)
        self.assertIn(b"Drag & Drop", response.data)

    def test_rules_page(self):
        response = self.client.get('/rules')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"LM001", response.data)
        self.assertIn(b"Legal Metrology Act, 2009", response.data)

    def test_sample_scenario_compliant(self):
        response = self.client.get('/sample/compliant', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"PASS", response.data)
        self.assertIn(b"100", response.data) # 100% compliance

    def test_sample_scenario_missing(self):
        response = self.client.get('/sample/missing', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"FAIL", response.data)

    def test_sample_scenario_blurry(self):
        response = self.client.get('/sample/blurry', follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        # Should render result with either REVIEW or FAIL depending on blur
        self.assertIn(b"Label Compliance Verification Report", response.data)

    def test_history_page(self):
        response = self.client.get('/history')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Historical Records", response.data)

    def test_pdf_report_download(self):
        # Trigger compliant scan first to get a scan ID
        sample_res = self.client.get('/sample/compliant', follow_redirects=True)
        self.assertEqual(sample_res.status_code, 200)
        
        # Download report for scan 1
        pdf_res = self.client.get('/report/1')
        self.assertEqual(pdf_res.status_code, 200)
        self.assertEqual(pdf_res.mimetype, 'application/pdf')

    def test_add_rule(self):
        post_data = {
            "rule_code": "LM008",
            "field_name": "Importer Name",
            "requirement": "Country of import and importer declaration required",
            "applicability": "Imported goods",
            "validation_type": "required",
            "source_document": "Legal Metrology Rules, 2011",
            "severity": "HIGH",
            "error_message": "Importer name not found."
        }
        res = self.client.post('/rules/add', data=post_data, follow_redirects=True)
        self.assertEqual(res.status_code, 200)
    def test_delete_history_item(self):
        # Trigger compliant scan first to get a record
        self.client.get('/sample/compliant', follow_redirects=True)
        from database import get_all_scans
        scans = get_all_scans()
        self.assertTrue(len(scans) > 0)
        target_id = scans[0]['id']
        del_res = self.client.post(f'/history/delete/{target_id}', follow_redirects=True)
        self.assertEqual(del_res.status_code, 200)
        self.assertIn(b"successfully deleted", del_res.data)

if __name__ == '__main__':
    unittest.main()


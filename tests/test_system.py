import os
import sys
import unittest
import tempfile
import sqlite3
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import Config
from database import init_db, get_all_rules, get_active_rules, save_scan, get_scan_by_id
from extractor import normalize_text, extract_product_name, extract_mrp, extract_net_quantity, extract_manufacturer, extract_address, extract_consumer_care, extract_all_fields
from compliance import evaluate_compliance
from report import generate_pdf_report
from ocr import preprocess_image, extract_text_from_image
from sample_generator import create_sample_labels

class LegalMetrologySystemTests(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        """Initializes database and generates sample images for testing."""
        init_db()
        cls.samples = create_sample_labels()

    def test_database_initialization(self):
        """Test that SQLite database initializes with default Legal Metrology rules."""
        rules = get_all_rules()
        self.assertGreaterEqual(len(rules), 6, "Database should contain at least 6 Legal Metrology rules")
        
        rule_codes = [r["rule_code"] for r in rules]
        self.assertIn("LM001", rule_codes)
        self.assertIn("LM002", rule_codes)
        self.assertIn("LM003", rule_codes)
        self.assertIn("LM004", rule_codes)
        self.assertIn("LM005", rule_codes)
        self.assertIn("LM006", rule_codes)

    def test_text_normalization(self):
        """Test text normalization removes irregular characters and standardizes format."""
        raw = "  ABC SHAMPOO \r\n\r\n MRP: ₹ 210.00 \n\n Net Qty: 180 ml  "
        normalized = normalize_text(raw)
        self.assertIn("ABC SHAMPOO", normalized)
        self.assertIn("MRP: ₹ 210.00", normalized)
        self.assertFalse("\r" in normalized)

    def test_mrp_extraction(self):
        """Test detection of various MRP declaration formats."""
        cases = [
            ("MRP: ₹210", 210.0, "Detected"),
            ("M.R.P. Rs. 210.00 (Incl. of all taxes)", 210.0, "Detected"),
            ("Maximum Retail Price: INR 450/-", 450.0, "Detected"),
            ("MRP 99.50", 99.5, "Detected"),
            ("MRP: ???", None, "Review Required"),
            ("No price printed here", None, "Not Detected")
        ]
        for text, expected_val, expected_status in cases:
            res = extract_mrp(text)
            self.assertEqual(res["status"], expected_status)
            if expected_val is not None:
                self.assertEqual(res["numeric_value"], expected_val)

    def test_net_quantity_extraction(self):
        """Test net quantity extraction with standard Legal Metrology units."""
        cases = [
            ("Net Quantity: 180 ml", 180.0, "ml"),
            ("Net Qty: 1 kg", 1.0, "kg"),
            ("Net Weight: 500 g", 500.0, "g"),
            ("Contents: 2.5 l", 2.5, "l"),
            ("Net Qty: 50 mg", 50.0, "mg")
        ]
        for text, expected_val, expected_unit in cases:
            res = extract_net_quantity(text)
            self.assertEqual(res["status"], "Detected")
            self.assertEqual(res["numeric_value"], expected_val)
            self.assertEqual(res["unit"], expected_unit)

    def test_manufacturer_and_address_extraction(self):
        """Test extraction of manufacturer name and manufacturing address."""
        text = (
            "Manufactured by: ABC Products Pvt Ltd\n"
            "Address: Plot 45, IDA Mallapur, Hyderabad, Telangana - 500076"
        )
        lines = text.split("\n")
        mfg = extract_manufacturer(text, lines)
        self.assertEqual(mfg["status"], "Detected")
        self.assertIn("ABC Products Pvt Ltd", mfg["value"])

        addr = extract_address(text, lines, mfg)
        self.assertEqual(addr["status"], "Detected")
        self.assertIn("Hyderabad", addr["value"])

    def test_consumer_care_extraction(self):
        """Test grievance redressal / customer care channel detection."""
        text = "Consumer Care Toll Free: 1800-123-456\nEmail: care@abcproducts.com"
        care = extract_consumer_care(text)
        self.assertEqual(care["status"], "Detected")
        self.assertIn("1800-123-456", care["value"])
        self.assertIn("care@abcproducts.com", care["value"])

    def test_compliance_engine_evaluation_pass(self):
        """Test compliance evaluation on fully compliant extracted dataset."""
        sample_text = (
            "ABC SHAMPOO\n"
            "MRP: ₹210\n"
            "Net Quantity: 180 ml\n"
            "Manufactured by: ABC Products Pvt Ltd\n"
            "Address: Hyderabad, Telangana\n"
            "Consumer Care: 1800-123-456\n"
        )
        extracted = extract_all_fields(sample_text)
        comp = evaluate_compliance(extracted)
        self.assertEqual(comp["overall_status"], "PASS")
        self.assertEqual(comp["compliance_score"], 100.0)
        self.assertEqual(comp["failed_checks"], 0)

    def test_compliance_engine_evaluation_fail(self):
        """Test compliance evaluation when mandatory fields are missing."""
        sample_text = (
            "ABC SHAMPOO\n"
            "MRP: ₹210\n"
            "Net Quantity: 180 ml\n"
            # Missing manufacturer & address
            "Consumer Care: 1800-123-456\n"
        )
        extracted = extract_all_fields(sample_text)
        comp = evaluate_compliance(extracted)
        self.assertEqual(comp["overall_status"], "FAIL")
        self.assertGreater(comp["failed_checks"], 0)
        self.assertLess(comp["compliance_score"], 100.0)

    def test_pdf_report_generation(self):
        """Test ReportLab PDF report generation creates valid PDF file."""
        sample_text = (
            "ABC SHAMPOO\n"
            "MRP: ₹210\n"
            "Net Quantity: 180 ml\n"
            "Manufactured by: ABC Products Pvt Ltd\n"
            "Address: Hyderabad, Telangana\n"
            "Consumer Care: 1800-123-456\n"
        )
        extracted = extract_all_fields(sample_text)
        comp = evaluate_compliance(extracted)
        
        pdf_path = generate_pdf_report(
            scan_id=999,
            filename="unit_test_sample.png",
            scan_date="2026-09-21 12:00:00",
            compliance_score=comp["compliance_score"],
            overall_status=comp["overall_status"],
            extracted_data=extracted,
            ocr_text=sample_text,
            rule_results=comp["rule_results"]
        )
        self.assertTrue(os.path.exists(pdf_path), "PDF report file should exist on disk")
        self.assertGreater(os.path.getsize(pdf_path), 1000, "PDF should not be empty")

    def test_opencv_preprocessing(self):
        """Test OpenCV preprocessing executes grayscale, blur, and thresholding."""
        sample_img_path = self.samples[0]
        self.assertTrue(os.path.exists(sample_img_path))
        processed_img, info = preprocess_image(sample_img_path)
        self.assertIsNotNone(processed_img)
        self.assertIn("pipeline", info)
        self.assertEqual(len(processed_img.shape), 2, "Processed image should be single-channel binarized")

if __name__ == "__main__":
    unittest.main()

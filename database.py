import sqlite3
import json
import os
from datetime import datetime
from config import Config

def get_db_connection():
    """Establishes connection to the SQLite database with Row factory and busy timeout."""
    os.makedirs(Config.DATABASE_FOLDER, exist_ok=True)
    conn = sqlite3.connect(Config.DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initializes the database tables and inserts prototype Legal Metrology rules."""
    os.makedirs(Config.DATABASE_FOLDER, exist_ok=True)
    conn = get_db_connection()
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass
    cursor = conn.cursor()

    # Create rules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_code TEXT UNIQUE NOT NULL,
            field_name TEXT NOT NULL,
            requirement TEXT NOT NULL,
            applicability TEXT NOT NULL,
            validation_type TEXT NOT NULL,
            validation_condition TEXT,
            source_document TEXT NOT NULL,
            rule_version TEXT NOT NULL,
            effective_date TEXT,
            severity TEXT NOT NULL,
            error_message TEXT,
            active INTEGER DEFAULT 1
        )
    """)

    # Create scan_history table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scan_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT NOT NULL,
            scan_date TEXT NOT NULL,
            compliance_score REAL NOT NULL,
            overall_status TEXT NOT NULL,
            extracted_data TEXT NOT NULL,
            ocr_text TEXT,
            image_path TEXT,
            report_path TEXT
        )
    """)

    # Seed initial prototype Legal Metrology rules if not present
    cursor.execute("SELECT COUNT(*) as cnt FROM rules")
    count = cursor.fetchone()["cnt"]

    if count == 0:
        initial_rules = [
            (
                "LM001",
                "Product Name",
                "Generic or common name of the commodity must be prominently declared",
                "All packaged commodities",
                "required",
                "non_empty",
                "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(a)",
                "2011-Rev2022",
                "2011-04-01",
                "HIGH",
                "Product name / commodity declaration could not be detected on the package label.",
                1
            ),
            (
                "LM002",
                "Net Quantity",
                "Net quantity in terms of standard unit of weight or measure must be declared",
                "Solid, liquid, and semi-solid packaged commodities",
                "valid_unit",
                "standard_units",
                "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(b) & Rule 12",
                "2011-Rev2022",
                "2011-04-01",
                "HIGH",
                "Net quantity is missing or does not use standardized Legal Metrology metric units (g, kg, ml, l, mg).",
                1
            ),
            (
                "LM003",
                "MRP",
                "Maximum Retail Price inclusive of all taxes must be clearly declared",
                "All retail packaged commodities meant for sale in India",
                "numeric_gt_zero",
                "positive_number",
                "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(e)",
                "2011-Rev2022",
                "2011-04-01",
                "CRITICAL",
                "Maximum Retail Price (MRP) declaration is missing or does not contain a valid positive monetary value.",
                1
            ),
            (
                "LM004",
                "Manufacturer",
                "Name of the manufacturer, packer, or importer must be clearly declared",
                "All packaged commodities",
                "required",
                "non_empty",
                "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(d)",
                "2011-Rev2022",
                "2011-04-01",
                "HIGH",
                "Manufacturer or Packer name could not be identified on the package label.",
                1
            ),
            (
                "LM005",
                "Manufacturer Address",
                "Complete physical premises or factory address of manufacturer/packer must be provided",
                "All packaged commodities",
                "required",
                "contains_location",
                "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(d)",
                "2011-Rev2022",
                "2011-04-01",
                "MEDIUM",
                "Manufacturer or packer physical address could not be reliably verified.",
                1
            ),
            (
                "LM006",
                "Consumer Care",
                "Name, address, telephone number or email of consumer care executive must be printed",
                "All retail packaged commodities",
                "contact_valid",
                "phone_or_email",
                "Legal Metrology (Packaged Commodities) Rules, 2011 - Rule 6(1)(n)",
                "2011-Rev2022",
                "2011-04-01",
                "HIGH",
                "Consumer care helpline number or email address could not be detected for grievance redressal.",
                1
            )
        ]

        cursor.executemany("""
            INSERT INTO rules (
                rule_code, field_name, requirement, applicability, validation_type,
                validation_condition, source_document, rule_version, effective_date,
                severity, error_message, active
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, initial_rules)

    conn.commit()
    conn.close()

def get_all_rules():
    """Retrieves all rules sorted by rule_code."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules ORDER BY rule_code ASC")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rules

def get_active_rules():
    """Retrieves all currently active compliance rules."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules WHERE active = 1 ORDER BY rule_code ASC")
    rules = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return rules

def get_rule_by_id(rule_id):
    """Retrieves a single rule by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM rules WHERE id = ?", (rule_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def add_rule(rule_data):
    """Adds a new Legal Metrology rule."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rules (
            rule_code, field_name, requirement, applicability, validation_type,
            validation_condition, source_document, rule_version, effective_date,
            severity, error_message, active
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        rule_data.get("rule_code"),
        rule_data.get("field_name"),
        rule_data.get("requirement"),
        rule_data.get("applicability", "All packaged commodities"),
        rule_data.get("validation_type", "required"),
        rule_data.get("validation_condition", "non_empty"),
        rule_data.get("source_document", "Legal Metrology Rules, 2011"),
        rule_data.get("rule_version", "1.0"),
        rule_data.get("effective_date", datetime.now().strftime("%Y-%m-%d")),
        rule_data.get("severity", "MEDIUM"),
        rule_data.get("error_message", "Requirement declaration not detected."),
        int(rule_data.get("active", 1))
    ))
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def update_rule(rule_id, rule_data):
    """Updates an existing Legal Metrology rule."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE rules SET
            rule_code = ?,
            field_name = ?,
            requirement = ?,
            applicability = ?,
            validation_type = ?,
            validation_condition = ?,
            source_document = ?,
            rule_version = ?,
            effective_date = ?,
            severity = ?,
            error_message = ?,
            active = ?
        WHERE id = ?
    """, (
        rule_data.get("rule_code"),
        rule_data.get("field_name"),
        rule_data.get("requirement"),
        rule_data.get("applicability"),
        rule_data.get("validation_type"),
        rule_data.get("validation_condition"),
        rule_data.get("source_document"),
        rule_data.get("rule_version"),
        rule_data.get("effective_date"),
        rule_data.get("severity"),
        rule_data.get("error_message"),
        int(rule_data.get("active", 1)),
        rule_id
    ))
    conn.commit()
    conn.close()

def toggle_rule_status(rule_id):
    """Toggles active state (0 or 1) of a rule."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT active FROM rules WHERE id = ?", (rule_id,))
    row = cursor.fetchone()
    if row:
        new_status = 0 if row["active"] == 1 else 1
        cursor.execute("UPDATE rules SET active = ? WHERE id = ?", (new_status, rule_id))
        conn.commit()
    conn.close()

def save_scan(filename, compliance_score, overall_status, extracted_data, ocr_text, image_path, report_path=None):
    """Persists a label scan result into the database."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO scan_history (
            filename, scan_date, compliance_score, overall_status,
            extracted_data, ocr_text, image_path, report_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        filename,
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        compliance_score,
        overall_status,
        json.dumps(extracted_data),
        ocr_text,
        image_path,
        report_path
    ))
    conn.commit()
    scan_id = cursor.lastrowid
    conn.close()
    return scan_id

def update_scan_report_path(scan_id, report_path):
    """Updates the generated PDF report path for a scan."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE scan_history SET report_path = ? WHERE id = ?", (report_path, scan_id))
    conn.commit()
    conn.close()

def get_scan_by_id(scan_id):
    """Retrieves a single scan result by ID with parsed JSON data."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_history WHERE id = ?", (scan_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    data = dict(row)
    try:
        data["extracted_data"] = json.loads(data["extracted_data"])
    except Exception:
        pass
    return data

def get_all_scans():
    """Retrieves all past scan records ordered by newest first."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM scan_history ORDER BY id DESC")
    scans = []
    for row in cursor.fetchall():
        d = dict(row)
        try:
            d["extracted_data"] = json.loads(d["extracted_data"])
        except Exception:
            pass
        scans.append(d)
    conn.close()
    return scans

def get_scan_statistics():
    """Calculates summary statistics for dashboard display."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as total FROM scan_history")
    total = cursor.fetchone()["total"]
    
    cursor.execute("SELECT COUNT(*) as passed FROM scan_history WHERE overall_status = 'PASS'")
    passed = cursor.fetchone()["passed"]
    
    cursor.execute("SELECT COUNT(*) as failed FROM scan_history WHERE overall_status = 'FAIL'")
    failed = cursor.fetchone()["failed"]
    
    cursor.execute("SELECT COUNT(*) as review FROM scan_history WHERE overall_status = 'REVIEW'")
    review = cursor.fetchone()["review"]
    
    cursor.execute("SELECT AVG(compliance_score) as avg_score FROM scan_history")
    avg_row = cursor.fetchone()
    avg_score = round(avg_row["avg_score"], 1) if avg_row and avg_row["avg_score"] is not None else 0.0

    conn.close()
    return {
        "total": total,
        "passed": passed,
        "failed": failed,
        "review": review,
        "avg_score": avg_score
    }

def delete_scan(scan_id):
    """Deletes a single scan history record by ID and returns its file paths."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image_path, report_path FROM scan_history WHERE id = ?", (scan_id,))
    row = cursor.fetchone()
    if row:
        cursor.execute("DELETE FROM scan_history WHERE id = ?", (scan_id,))
        conn.commit()
        conn.close()
        return dict(row)
    conn.close()
    return None

def clear_all_scans():
    """Deletes all scan history records from the database and returns all file paths."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT image_path, report_path FROM scan_history")
    rows = [dict(r) for r in cursor.fetchall()]
    cursor.execute("DELETE FROM scan_history")
    conn.commit()
    conn.close()
    return rows


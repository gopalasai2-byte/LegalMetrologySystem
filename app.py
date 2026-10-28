import os
import shutil
from flask import Flask, send_from_directory, render_template, request, redirect, url_for, flash, send_file, jsonify
from werkzeug.utils import secure_filename

from config import Config
from database import (
    init_db, get_all_rules, get_active_rules, get_rule_by_id, add_rule, update_rule,
    toggle_rule_status, save_scan, update_scan_report_path, get_scan_by_id,
    get_all_scans, get_scan_statistics, delete_scan, clear_all_scans
)
from utils import allowed_file, generate_unique_filename, ensure_project_directories
from ocr import extract_text_from_image, is_tesseract_available, is_any_ocr_available, rapid_engine
from extractor import extract_all_fields
from compliance import evaluate_compliance
from report import generate_pdf_report
from sample_generator import create_sample_labels

app = Flask(__name__)
app.config.from_object(Config)

# Ensure required runtime directories and SQLite database exist
ensure_project_directories()
init_db()

# Ensure demo sample labels exist
create_sample_labels()

@app.context_processor
def inject_global_vars():
    """Provides system status across all templates."""
    tess_available = is_tesseract_available()
    rapid_available = (rapid_engine is not None)
    ocr_active = rapid_available or tess_available
    
    if rapid_available:
        engine_name = "RapidOCR (Deep Learning PP-OCRv4)"
    elif tess_available:
        engine_name = "Tesseract OCR (LSTM Neural Net)"
    else:
        engine_name = "Demo / Fallback Mode"

    return {
        "ocr_active": ocr_active,
        "ocr_engine_name": engine_name,
        "tesseract_available": tess_available,
        "tesseract_path": Config.get_tesseract_cmd() or "N/A"
    }

@app.route("/")
def index():
    """Homepage dashboard showing overview statistics, project principles, and recent scans."""
    stats = get_scan_statistics()
    recent_scans = get_all_scans()[:5]
    return render_template("index.html", stats=stats, recent_scans=recent_scans)

@app.route("/check")
def check():
    """Label upload interface with drag-and-drop and preloaded scenario buttons."""
    return render_template("check.html")

@app.route("/upload", methods=["POST"])
def upload_file():
    """Processes uploaded label image through OpenCV, OCR, Extractor, and Compliance Engine."""
    if "label_image" not in request.files:
        flash("No file part provided in the request.", "danger")
        return redirect(url_for("check"))

    file = request.files["label_image"]
    if file.filename == "":
        flash("No file was selected for upload.", "warning")
        return redirect(url_for("check"))

    if not allowed_file(file.filename):
        flash("Unsupported file format. Please upload JPG, JPEG, PNG, or WEBP images.", "danger")
        return redirect(url_for("check"))

    try:
        unique_name = generate_unique_filename(file.filename)
        saved_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
        file.save(saved_path)

        # Run OCR extraction pipeline
        ocr_result = extract_text_from_image(saved_path)
        raw_text = ocr_result.get("raw_text", "")

        # Extract structured fields
        extracted = extract_all_fields(raw_text)

        # Run Legal Metrology compliance engine
        compliance_result = evaluate_compliance(extracted)

        # Save initial scan record in database
        scan_id = save_scan(
            filename=file.filename,
            compliance_score=compliance_result["compliance_score"],
            overall_status=compliance_result["overall_status"],
            extracted_data=extracted,
            ocr_text=raw_text,
            image_path=unique_name,
            report_path=None
        )

        # Generate formal PDF report
        pdf_path = generate_pdf_report(
            scan_id=scan_id,
            filename=file.filename,
            scan_date="Current Audit Session",
            compliance_score=compliance_result["compliance_score"],
            overall_status=compliance_result["overall_status"],
            extracted_data=extracted,
            ocr_text=raw_text,
            rule_results=compliance_result["rule_results"]
        )
        update_scan_report_path(scan_id, os.path.basename(pdf_path))

        if not ocr_result.get("tesseract_installed"):
            flash(
                "Notice: Tesseract OCR is not installed locally. "
                "The system used demo label matching for evaluation. "
                "Install Tesseract OCR on Windows for full live camera image extraction.",
                "info"
            )

        return redirect(url_for("result", scan_id=scan_id))

    except Exception as e:
        flash(f"An error occurred while processing the label: {str(e)}", "danger")
        return redirect(url_for("check"))

@app.route("/sample/<scenario>")
def run_sample(scenario):
    """
    Directly tests one of the 3 predefined demonstration scenarios:
    - compliant: Scenario 1 (Fully compliant shampoo label)
    - missing: Scenario 2 (Missing manufacturer and address)
    - blurry: Scenario 3 (Degraded OCR / Review required)
    """
    filename_map = {
        "compliant": "sample_compliant.png",
        "missing": "sample_missing.png",
        "blurry": "sample_blurry.png"
    }

    if scenario not in filename_map:
        flash("Unknown sample scenario.", "danger")
        return redirect(url_for("check"))

    sample_src = os.path.join(Config.SAMPLE_FOLDER, filename_map[scenario])
    if not os.path.exists(sample_src):
        create_sample_labels()

    # Copy to uploads folder with unique name
    unique_name = generate_unique_filename(filename_map[scenario])
    dest_path = os.path.join(Config.UPLOAD_FOLDER, unique_name)
    shutil.copyfile(sample_src, dest_path)

    # Process through pipeline
    ocr_result = extract_text_from_image(dest_path)
    raw_text = ocr_result.get("raw_text", "")
    extracted = extract_all_fields(raw_text)
    compliance_result = evaluate_compliance(extracted)

    scan_id = save_scan(
        filename=filename_map[scenario],
        compliance_score=compliance_result["compliance_score"],
        overall_status=compliance_result["overall_status"],
        extracted_data=extracted,
        ocr_text=raw_text,
        image_path=unique_name,
        report_path=None
    )

    pdf_path = generate_pdf_report(
        scan_id=scan_id,
        filename=filename_map[scenario],
        scan_date="Demonstration Audit Session",
        compliance_score=compliance_result["compliance_score"],
        overall_status=compliance_result["overall_status"],
        extracted_data=extracted,
        ocr_text=raw_text,
        rule_results=compliance_result["rule_results"]
    )
    update_scan_report_path(scan_id, os.path.basename(pdf_path))

    flash(f"Demonstration scenario '{scenario.title()}' processed successfully.", "success")
    return redirect(url_for("result", scan_id=scan_id))

@app.route("/result/<int:scan_id>")
def result(scan_id):
    """Displays detailed compliance audit report dashboard for a specific scan."""
    scan = get_scan_by_id(scan_id)
    if not scan:
        flash("Requested scan record not found.", "warning")
        return redirect(url_for("history"))

    extracted_data = scan.get("extracted_data", {})
    compliance_result = evaluate_compliance(extracted_data)

    return render_template(
        "result.html",
        scan=scan,
        extracted=extracted_data,
        compliance=compliance_result
    )

@app.route("/history")
def history():
    """Displays chronological history of all packaged commodity label scans."""
    scans = get_all_scans()
    return render_template("history.html", scans=scans)

@app.route("/history/delete/<int:scan_id>", methods=["POST"])
def delete_history_item(scan_id):
    """Deletes a specific scan record and cleans up associated files."""
    deleted = delete_scan(scan_id)
    if deleted:
        try:
            if deleted.get("image_path"):
                img_path = os.path.join(Config.UPLOAD_FOLDER, deleted["image_path"])
                if os.path.exists(img_path):
                    os.remove(img_path)
            if deleted.get("report_path") and os.path.exists(deleted["report_path"]):
                os.remove(deleted["report_path"])
        except Exception:
            pass
        flash(f"Scan record #LMC-{scan_id:04d} was successfully deleted.", "success")
    else:
        flash("Scan record not found or could not be deleted.", "warning")
    return redirect(url_for("history"))

@app.route("/history/clear", methods=["POST"])
def clear_history():
    """Clears all scan history records from the database and cleans up files."""
    scans = clear_all_scans()
    count = len(scans)
    for s in scans:
        try:
            if s.get("image_path"):
                img_path = os.path.join(Config.UPLOAD_FOLDER, s["image_path"])
                if os.path.exists(img_path):
                    os.remove(img_path)
            if s.get("report_path") and os.path.exists(s["report_path"]):
                os.remove(s["report_path"])
        except Exception:
            pass
    flash(f"All {count} scan history record(s) have been permanently cleared.", "info")
    return redirect(url_for("history"))

@app.route("/rules")
def rules():
    """Legal Metrology Rule Management and Legal Source Reference page."""
    all_rules = get_all_rules()
    return render_template("rules.html", rules=all_rules)

@app.route("/rules/add", methods=["POST"])
def add_new_rule():
    """Adds a new Legal Metrology compliance rule to the database."""
    rule_data = {
        "rule_code": request.form.get("rule_code", "").strip().upper(),
        "field_name": request.form.get("field_name", "").strip(),
        "requirement": request.form.get("requirement", "").strip(),
        "applicability": request.form.get("applicability", "All packaged commodities").strip(),
        "validation_type": request.form.get("validation_type", "required").strip(),
        "validation_condition": request.form.get("validation_condition", "non_empty").strip(),
        "source_document": request.form.get("source_document", "Legal Metrology Rules, 2011").strip(),
        "rule_version": request.form.get("rule_version", "1.0").strip(),
        "severity": request.form.get("severity", "MEDIUM").strip(),
        "error_message": request.form.get("error_message", "Requirement declaration not detected.").strip(),
        "active": 1
    }

    if not rule_data["rule_code"] or not rule_data["field_name"] or not rule_data["requirement"]:
        flash("Rule Code, Field Name, and Legal Requirement are mandatory.", "danger")
        return redirect(url_for("rules"))

    try:
        add_rule(rule_data)
        flash(f"Rule {rule_data['rule_code']} added successfully.", "success")
    except Exception as e:
        flash(f"Failed to add rule: {str(e)}", "danger")

    return redirect(url_for("rules"))

@app.route("/rules/toggle/<int:rule_id>", methods=["POST"])
def toggle_rule(rule_id):
    """Enables or disables a Legal Metrology rule."""
    try:
        toggle_rule_status(rule_id)
        flash("Rule status updated.", "info")
    except Exception as e:
        flash(f"Failed to update rule status: {str(e)}", "danger")
    return redirect(url_for("rules"))

@app.route("/report/<int:scan_id>")
def download_report(scan_id):
    """Serves the generated PDF audit report for download."""
    scan = get_scan_by_id(scan_id)
    if not scan or not scan.get("report_path"):
        flash("Report not found for this scan.", "warning")
        return redirect(url_for("history"))

    report_file = os.path.join(Config.REPORT_FOLDER, scan["report_path"])
    if not os.path.exists(report_file):
        # Re-generate report if file is missing
        extracted = scan.get("extracted_data", {})
        comp = evaluate_compliance(extracted)
        report_file = generate_pdf_report(
            scan_id=scan["id"],
            filename=scan["filename"],
            scan_date=scan["scan_date"],
            compliance_score=scan["compliance_score"],
            overall_status=scan["overall_status"],
            extracted_data=extracted,
            ocr_text=scan.get("ocr_text", ""),
            rule_results=comp["rule_results"]
        )
        update_scan_report_path(scan_id, os.path.basename(report_file))

    return send_file(
        report_file,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"Legal_Metrology_Report_Scan_{scan_id}.pdf"
    )

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    """Serves uploaded label images."""
    file_path = os.path.join(Config.UPLOAD_FOLDER, filename)
    if not os.path.exists(file_path):
        # Fallback check in samples
        sample_path = os.path.join(Config.SAMPLE_FOLDER, filename)
        if os.path.exists(sample_path):
            return send_file(sample_path)
        flash("Image file not found.", "warning")
        return redirect(url_for("index"))
    return send_file(file_path)

@app.errorhandler(404)
def not_found_error(error):
    return render_template("error.html", code=404, message="The requested page could not be found."), 404

@app.errorhandler(413)
def file_too_large(error):
    return render_template("error.html", code=413, message="The uploaded image exceeds the 16MB file size limit."), 413

@app.errorhandler(500)
def internal_error(error):
    return render_template("error.html", code=500, message="An internal server error occurred while processing the request."), 500

if __name__ == "__main__":
    print("=" * 70)
    print(" LEGAL METROLOGY COMPLIANCE VERIFICATION SYSTEM")
    print(" Packaged Commodities Label Audit Web Application")
    print("=" * 70)
    print(f" * Database initialized: {Config.DATABASE_PATH}")
    print(f" * Tesseract status: {'FOUND' if is_tesseract_available() else 'NOT DETECTED (Fallback Mode Active)'}")
    print(f" * Server running on: http://127.0.0.1:5000")
    print("=" * 70)
    app.run(host="127.0.0.1", port=5000, debug=True)

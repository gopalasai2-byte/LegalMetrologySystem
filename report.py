import os
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from config import Config

def generate_pdf_report(scan_id, filename, scan_date, compliance_score, overall_status, extracted_data, ocr_text, rule_results):
    """
    Generates a formal PDF Compliance Report using ReportLab.
    
    Returns:
        output_pdf_path (str): File path to generated PDF
    """
    os.makedirs(Config.REPORT_FOLDER, exist_ok=True)
    pdf_filename = f"Compliance_Report_Scan_{scan_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    output_path = os.path.join(Config.REPORT_FOLDER, pdf_filename)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0f172a"),
        alignment=1 # Center
    )

    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=8,
        spaceAfter=4
    )

    cell_bold = ParagraphStyle(
        'CellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor("#1e293b")
    )

    cell_normal = ParagraphStyle(
        'CellNormal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#334155")
    )

    ocr_style = ParagraphStyle(
        'OCRStyle',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=9.5,
        textColor=colors.HexColor("#334155")
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerStyle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    story = []

    # Title and Subtitle
    story.append(Paragraph("GOVERNMENT / REGULATORY VERIFICATION AUDIT", subtitle_style))
    story.append(Spacer(1, 4))
    story.append(Paragraph("LEGAL METROLOGY COMPLIANCE VERIFICATION REPORT", title_style))
    story.append(Paragraph("Automated Label Audit under Legal Metrology (Packaged Commodities) Rules, 2011", subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=10))

    # Meta information table
    status_bg = "#10b981" if overall_status == "PASS" else ("#ef4444" if overall_status == "FAIL" else "#f59e0b")
    
    meta_data = [
        [
            Paragraph("<b>Scan Reference ID:</b>", cell_bold),
            Paragraph(f"LMC-{scan_id:05d}", cell_normal),
            Paragraph("<b>Audit Date & Time:</b>", cell_bold),
            Paragraph(str(scan_date), cell_normal)
        ],
        [
            Paragraph("<b>Original Image File:</b>", cell_bold),
            Paragraph(str(filename), cell_normal),
            Paragraph("<b>Preliminary Result:</b>", cell_bold),
            Paragraph(f"<font color='{status_bg}'><b>{overall_status}</b> ({compliance_score}%)</font>", cell_bold)
        ]
    ]

    meta_table = Table(meta_data, colWidths=[120, 160, 120, 140])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#e2e8f0")),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 12))

    # Extracted Declarations
    story.append(Paragraph("1. Extracted Package Declarations (OCR & NLP)", section_heading))
    
    fields = extracted_data.get("fields", {})
    field_rows = [
        [
            Paragraph("<b>Declaration Field</b>", cell_bold),
            Paragraph("<b>Detected Value from Label</b>", cell_bold),
            Paragraph("<b>Confidence / Status</b>", cell_bold)
        ]
    ]

    for fname, fval in fields.items():
        val = fval.get("value") or "Not Detected"
        f_status = fval.get("status", "Unknown")
        color_tag = "#10b981" if f_status == "Detected" else "#ef4444"
        field_rows.append([
            Paragraph(fname, cell_bold),
            Paragraph(str(val), cell_normal),
            Paragraph(f"<font color='{color_tag}'><b>{f_status}</b></font>", cell_normal)
        ])

    decl_table = Table(field_rows, colWidths=[140, 280, 120])
    decl_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(decl_table)
    story.append(Spacer(1, 12))

    # Compliance Engine Rule Results Table
    story.append(Paragraph("2. Rule-Based Compliance Evaluation Findings", section_heading))
    
    rule_rows = [
        [
            Paragraph("<b>Rule Code</b>", cell_bold),
            Paragraph("<b>Legal Requirement</b>", cell_bold),
            Paragraph("<b>Extracted Declaration</b>", cell_bold),
            Paragraph("<b>Rule Status</b>", cell_bold)
        ]
    ]

    for r in rule_results:
        st = r.get("status", "REVIEW")
        bg_col = "#10b981" if st == "PASS" else ("#ef4444" if st == "FAIL" else "#f59e0b")
        rule_rows.append([
            Paragraph(r.get("rule_code", ""), cell_bold),
            Paragraph(r.get("requirement", ""), cell_normal),
            Paragraph(str(r.get("extracted_value", "")), cell_normal),
            Paragraph(f"<font color='{bg_col}'><b>{st}</b></font>", cell_bold)
        ])

    rule_table = Table(rule_rows, colWidths=[65, 235, 170, 70])
    rule_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#e2e8f0")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor("#f1f5f9")),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(rule_table)
    story.append(Spacer(1, 10))

    # Raw OCR Extract box
    story.append(Paragraph("3. Raw Text Transcript Extracted by OCR Engine", section_heading))
    sanitized_ocr = (ocr_text or "No text could be extracted.").replace("<", "&lt;").replace(">", "&gt;")
    # Truncate if excessively long
    if len(sanitized_ocr) > 1200:
        sanitized_ocr = sanitized_ocr[:1200] + "\n... [truncated for report length]"
        
    ocr_box = Table([[Paragraph(sanitized_ocr.replace("\n", "<br/>"), ocr_style)]], colWidths=[540])
    ocr_box.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('BOX', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(ocr_box)
    story.append(Spacer(1, 14))

    # Official Legal Disclaimer
    disclaimer_text = (
        "<b>LEGAL & AUDIT DISCLAIMER:</b> This report is a preliminary software-assisted verification "
        "of printed package information generated using Optical Character Recognition (OCR) and automated rule-checking. "
        "It is not a legal certification and should be reviewed against the applicable and current Legal Metrology requirements. "
        "Final compliance determinations must be validated by authorized Legal Metrology officers in accordance with the "
        "Legal Metrology Act, 2009 and Packaged Commodities Rules, 2011."
    )
    story.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(story)
    return output_path

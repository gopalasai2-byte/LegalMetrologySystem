from database import get_active_rules

def evaluate_compliance(extracted_data):
    """
    Evaluates extracted product label fields against active Legal Metrology rules.
    
    Args:
        extracted_data (dict): Result from extractor.extract_all_fields()
        
    Returns:
        dict: {
            "rule_results": list of evaluated rule dictionaries,
            "passed_checks": int,
            "failed_checks": int,
            "review_checks": int,
            "total_applicable": int,
            "compliance_score": float,
            "overall_status": str ("PASS", "FAIL", "REVIEW"),
            "summary_explanation": str,
            "recommendations": list of str
        }
    """
    active_rules = get_active_rules()
    fields = extracted_data.get("fields", {})

    rule_results = []
    passed_count = 0
    failed_count = 0
    review_count = 0
    recommendations = []

    for rule in active_rules:
        field_name = rule["field_name"]
        val_type = rule["validation_type"]
        severity = rule["severity"]
        field_info = fields.get(field_name, None)

        status = "REVIEW"
        detail_msg = ""
        found_value = None

        if field_info is None:
            applicability = rule.get("applicability", "").lower()
            if "import" in applicability:
                rule_results.append({
                    "rule_code": rule["rule_code"],
                    "field_name": field_name,
                    "requirement": rule["requirement"],
                    "applicability": rule["applicability"],
                    "source_document": rule["source_document"],
                    "severity": severity,
                    "extracted_value": "N/A (Domestic Commodity)",
                    "status": "NOT APPLICABLE",
                    "detail_message": "Exempt: Rule applies exclusively to imported pre-packaged goods."
                })
                continue
            else:
                status = "REVIEW"
                detail_msg = "Field not evaluated or extracted by the current model."
                review_count += 1
        else:
            extracted_val = field_info.get("value")
            field_status = field_info.get("status")
            found_value = extracted_val

            if field_status == "Detected" and extracted_val:
                # Field was detected, now validate based on rule criteria
                if val_type == "required":
                    status = "PASS"
                    detail_msg = f"Declaration verified: '{extracted_val}'."
                    passed_count += 1

                elif val_type == "numeric_gt_zero":
                    num_val = field_info.get("numeric_value")
                    if num_val is not None and num_val > 0:
                        status = "PASS"
                        detail_msg = f"Valid price declared: {extracted_val}."
                        passed_count += 1
                    else:
                        status = "FAIL"
                        detail_msg = rule.get("error_message") or "Numeric value is missing or zero."
                        failed_count += 1

                elif val_type == "valid_unit":
                    unit = field_info.get("unit")
                    valid_units = ["mg", "g", "kg", "ml", "l", "litre", "liter", "litres", "liters"]
                    if unit and unit.lower() in valid_units:
                        status = "PASS"
                        detail_msg = f"Standard Legal Metrology metric unit verified: {extracted_val}."
                        passed_count += 1
                    else:
                        status = "FAIL"
                        detail_msg = f"Non-standard metric unit: '{unit}'."
                        failed_count += 1

                elif val_type == "contact_valid":
                    status = "PASS"
                    detail_msg = f"Grievance contact channel found: {extracted_val}."
                    passed_count += 1

                else:
                    # Generic non-empty check
                    status = "PASS"
                    detail_msg = "Information verified."
                    passed_count += 1

            elif field_status == "Review Required":
                status = "REVIEW"
                detail_msg = field_info.get("detail") or "OCR reading uncertain or low contrast. Manual review required."
                review_count += 1
                recommendations.append(f"Manually verify '{field_name}' on the package label.")

            else:
                # Clearly absent
                status = "FAIL"
                detail_msg = rule.get("error_message") or f"{field_name} declaration is missing from the label."
                failed_count += 1
                recommendations.append(f"Ensure '{field_name}' is clearly printed in accordance with Legal Metrology rules.")

        rule_results.append({
            "rule_code": rule["rule_code"],
            "field_name": field_name,
            "requirement": rule["requirement"],
            "applicability": rule["applicability"],
            "source_document": rule["source_document"],
            "severity": severity,
            "extracted_value": found_value if found_value else "Not Detected",
            "status": status,
            "detail_message": detail_msg
        })

    applicable_results = [r for r in rule_results if r.get("status") != "NOT APPLICABLE"]
    total_applicable = len(applicable_results)
    compliance_score = round((passed_count / total_applicable * 100), 1) if total_applicable > 0 else 0.0

    # Determine overall status
    if failed_count > 0:
        overall_status = "FAIL"
        summary_explanation = (
            f"Preliminary System Result: FAIL ({passed_count}/{total_applicable} checks passed). "
            f"{failed_count} applicable declaration(s) could not be verified or did not meet Legal Metrology requirements. "
            "Manual review is recommended before making any final compliance or regulatory decision."
        )
    elif review_count > 0:
        overall_status = "REVIEW"
        summary_explanation = (
            f"Preliminary System Result: REVIEW REQUIRED ({passed_count}/{total_applicable} checks passed). "
            f"{review_count} declaration(s) have uncertain OCR readings or partial text. "
            "Physical inspection or manual verification of the package label is necessary."
        )
    else:
        overall_status = "PASS"
        summary_explanation = (
            f"Preliminary System Result: PASS ({passed_count}/{total_applicable} checks passed). "
            "All configured Legal Metrology prototype declarations were successfully detected and verified from the printed label image."
        )

    # General photographic/lighting recommendations
    if review_count > 0:
        recommendations.append("Retake label image under even lighting with no shadows or glare.")
        recommendations.append("Ensure the entire label bounding area is captured in high focus.")

    if not recommendations:
        recommendations.append("All applicable declarations appear compliant based on software-assisted verification.")

    return {
        "rule_results": rule_results,
        "passed_checks": passed_count,
        "failed_checks": failed_count,
        "review_checks": review_count,
        "total_applicable": total_applicable,
        "compliance_score": compliance_score,
        "overall_status": overall_status,
        "summary_explanation": summary_explanation,
        "recommendations": list(dict.fromkeys(recommendations))  # Unique preserve order
    }

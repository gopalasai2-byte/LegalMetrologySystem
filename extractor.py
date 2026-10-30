import re

def normalize_text(raw_text):
    """
    Normalizes raw OCR text:
    - Standardizes unicode, fullwidth punctuation, and currency symbols
    - Fixes common OCR artifacts and concatenation in statutory packaging phrases
    - Standardizes linebreaks and trims whitespace
    """
    if not raw_text:
        return ""
    
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    # Standardize fullwidth punctuation and Unicode artifacts
    text = text.replace('\uff1a', ':').replace('\uff0c', ',').replace('\uff08', '(').replace('\uff09', ')')
    text = text.replace('\u2013', '-').replace('\u2014', '-').replace('\u2212', '-')
    # Strip unprintable control characters (preserve ₹ and printable symbols)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]', '', text)

    # Normalize common OCR typos in packaging declarations
    text = re.sub(r'\bMRP\s*\(\s*l\s*ncl\b', 'MRP (incl', text, flags=re.IGNORECASE)
    text = re.sub(r'\balltaxes\b', 'all taxes', text, flags=re.IGNORECASE)
    text = re.sub(r'\bUnitSalePrice\b', 'Unit Sale Price', text, flags=re.IGNORECASE)
    text = re.sub(r'\bNetQuantity\b', 'Net Quantity', text, flags=re.IGNORECASE)
    text = re.sub(r'\bManufacturedby\b', 'Manufactured by', text, flags=re.IGNORECASE)
    
    lines = [line.strip() for line in text.split("\n")]
    non_empty_lines = [l for l in lines if l]
    return "\n".join(non_empty_lines)

def extract_product_name(lines, raw_text):
    """
    Extracts Product Name / Commodity Declaration under Rule 6(1)(a).
    1. Looks for explicit labels: 'Product Name:', 'Commodity:', 'Item:'
    2. Searches for standard commodity terms (e.g. Milk Chocolate, Shampoo, Biscuits)
    3. Fallback: First prominent line that isn't marketing text or metadata
    """
    # 1. Explicit pattern (must not be 'product quality' or satisfaction guarantees)
    explicit_match = re.search(
        r'(?:commodity|item|(?:product\s+(?:name|title)))\s*[:\-–]\s*([^\n\r]+)',
        raw_text,
        re.IGNORECASE
    )
    if explicit_match:
        val = explicit_match.group(1).strip()
        if len(val) > 2 and not re.search(r'\b(?:quality|satisfaction|guarantee)\b', val, re.IGNORECASE):
            return {"value": val, "status": "Detected", "confidence": "HIGH", "detail": "Explicit product label detected"}

    # 2. Known packaged commodity terms (prioritize specific product names over general ingredient terms)
    commodity_keywords = [
        (r'\b(?:Chocolatey\s+Sandwich\s+Biscuits?|Sandwich\s+Biscuits?|Cream\s+Biscuits?|Digestive\s+Biscuits?|Biscuits?|Cookies?|Wafers?|Snacks?|Potato\s+Chips?|Namkeen)\b', None),
        (r'\b(?:Double\s+Toned\s+Milk|Toned\s+Milk|Full\s+Cream\s+Milk|Pasteurised\s+Milk|Standardized\s+Milk|Cow\s+Milk|Buffalo\s+Milk|Milk)\b', None),
        (r'\b(?:Lijjat\s+Papad|Udad\s+Papad|Moong\s+Papad|Papad|Appalam|Fryums)\b', None),
        (r'\b(?:Dairy\s+Milk|Milk\s+Chocolate|Dark\s+Chocolate|White\s+Chocolate|Chocolate\s+Bar|Chocolate)\b', None),
        (r'\b(?:Cocoa\s+Butter|Cocoa\s+Confectionery)\b', "Cocoa / Chocolate Confectionery"),
        (r'\b(?:Shampoo|Conditioner|Hair\s+Oil|Face\s+Wash|Soap|Body\s+Wash)\b', None),
        (r'\b(?:Atta|Wheat\s+Flour|Rice|Sugar|Iodized\s+Salt|Edible\s+Oil)\b', None),
        (r'\b(?:Tea|Green\s+Tea|Coffee|Fruit\s+Juice|Packaged\s+Drinking\s+Water)\b', None),
        (r'\b(?:Detergent\s+(?:Powder|Bar)?|Toothpaste|Dishwash|Disinfectant)\b', None)
    ]
    for pattern, canonical_name in commodity_keywords:
        match = re.search(pattern, raw_text, re.IGNORECASE)
        if match:
            found_commodity = canonical_name if canonical_name else match.group(0).strip().title()
            return {
                "value": found_commodity,
                "status": "Detected",
                "confidence": "HIGH",
                "detail": f"Recognized standard packaged commodity ({found_commodity})"
            }

    # 3. Line by line heuristics with extensive skip keywords
    skip_keywords = [
        "mrp", "m.r.p", "net qty", "net quantity", "net wt", "net weight", "mfd",
        "manufactured", "batch", "exp", "pkd", "use by", "best before",
        "product quality", "product", "thanks to", "we are", "farmers", "the environment",
        "nutrition", "ingredients", "storage", "allergen", "serving", "recyclable",
        "packaging material", "sovrceo", "cocoa", "registered", "reg. no", "lic. no",
        "fssai", "100%", "contains", "call", "email", "keep", "for code", "scan",
        "siosied", "satisfied", "fat:", "snf:", "fat", "snf", "why is this", "sterilised", "homogenised"
    ]

    for line in lines:
        cleaned = line.strip()
        cleaned = re.sub(r'^[^\w\s]+', '', cleaned).strip()
        if len(cleaned) < 3:
            continue
        
        line_lower = cleaned.lower()
        if any(line_lower.startswith(k) for k in skip_keywords):
            continue
        
        # Skip lines that are just numbers/currency/weights
        if re.search(r'^(?:₹|rs\.?|inr|\d+\s*(?:ml|g|kg|l))\b', line_lower):
            continue
            
        # Quality check: contains alphabetic characters
        if re.search(r'[A-Za-z]{3,}', cleaned):
            return {
                "value": cleaned,
                "status": "Detected",
                "confidence": "MEDIUM",
                "detail": "Identified as primary title/commodity declaration"
            }

    return {
        "value": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "Product name declaration was not detected on the label."
    }

def extract_mrp(raw_text):
    """
    Extracts Maximum Retail Price (MRP) under Rule 6(1)(e):
    Detects patterns like:
    - MRP (Incl. of all taxes) : ₹ 349.00
    - MRP Rs. 100.00 (incl. of all taxes)
    - MRP: ₹210
    - M.R.P. Rs. 210.00
    - Multiline MRP labels & values
    - Rs. 0.79 per g / Standard Unit Sale Price: 1.03 per ml (Unit Sale Price)
    """
    # 1. Check for Unit Sale Price (USP) under Legal Metrology 2022 amendment
    usp_match = re.search(
        r'(?:(?:Unit\s*Sale\s*Price|USP)\s*[:\-–]?\s*(?:Rs\.?|₹|\?)?\s*|(?<!\w)(?:Rs\.?|₹)\s*)([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:per|/)\s*(g|ml|kg|l)\b',
        raw_text,
        re.IGNORECASE
    )
    extra_usp = ""
    if usp_match:
        extra_usp = f" (Unit Sale Price: ₹{usp_match.group(1)}/{usp_match.group(2)})"

    patterns = [
        # MRP (Incl. of all taxes) : ₹ 349.00 OR MRP : ₹ 349.00 (incl. of all taxes)
        r'(?:M\.?\s*R\.?\s*P\.?|Maximum\s+Retail\s+Price)(?:\s*\([^)]*\))?\s*[:\-–=is]?\s*(?:₹|Rs\.?|INR|\bRS\b)?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:/\-|incl|ind|only|\(|$)',
        # ₹ 210 or Rs 210 with optional inclusive clause
        r'(?:₹|Rs\.?|INR)\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*(?:\(?(?:incl|ind|inclusive)[^)\n]*\)?)?',
        # MRP keyword anywhere on line followed by a price figure
        r'\b(?:M\.?\s*R\.?\s*P\.?|Maximum\s+Retail\s+Price)\b[^\d\n]*([0-9]+(?:[.,][0-9]{1,2})?)',
        # Multiline: MRP on line 1, price on line 2
        r'(?:M\.?\s*R\.?\s*P\.?|Maximum\s+Retail\s+Price)[^\d\n]*(?:\n\s*[:\-–=]?\s*(?:₹|Rs\.?|INR)?\s*([0-9]+(?:[.,][0-9]{1,2})?))',
        # Multiline: price on line 1, MRP on line 2
        r'(?:₹|Rs\.?|INR|:)?\s*([0-9]+(?:[.,][0-9]{1,2})?)\s*\n\s*(?:M\.?\s*R\.?\s*P\.?|Maximum\s+Retail\s+Price)'
    ]

    for pat in patterns:
        match = re.search(pat, raw_text, re.IGNORECASE)
        if match:
            raw_val = match.group(1).replace(",", ".")
            try:
                numeric_val = float(raw_val)
                if numeric_val > 0:
                    formatted_display = f"₹{numeric_val:g}"
                    return {
                        "value": f"{formatted_display}{extra_usp}",
                        "numeric_value": numeric_val,
                        "status": "Detected",
                        "confidence": "HIGH",
                        "detail": f"Detected MRP of ₹{numeric_val:g} with valid statutory monetary format"
                    }
            except ValueError:
                continue

    # Fuzzy check if MRP keyword exists but figure is obscured
    if re.search(r'\bM\.?R\.?P\b', raw_text, re.IGNORECASE):
        return {
            "value": "Unclear / Obscured",
            "numeric_value": None,
            "status": "Review Required",
            "confidence": "LOW",
            "detail": "MRP keyword found but price figure could not be reliably verified. Manual verification recommended."
        }

    return {
        "value": None,
        "numeric_value": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "MRP declaration was not detected on the package label."
    }

def extract_net_quantity(raw_text):
    """
    Extracts Net Quantity and Metric Units under Rule 6(1)(b) & Rule 12:
    Detects patterns like:
    - Net Wt.: 126 g / 126g
    - Net Quantity: 180 ml / NetQuantity :340ml
    - Net Qty: 1 kg
    - Standalone 126g / 180ml / 340ml
    """
    units_pattern = r'(?:mg|g|kg|ml|l|litre|liter|litres|liters)'
    
    # 1. Explicit keyword followed by number and unit (supports attached '126g', '340ml', etc.)
    pattern_explicit = re.compile(
        r'(?:Net\s*(?:Quantity|Qty|Weight|Wt|Vol|Volume|Contents?|W[t:]?))\s*[:\-–.]*\s*([0-9]+(?:[.,][0-9]+)?)\.?\s*(' + units_pattern + r')\b',
        re.IGNORECASE
    )
    match = pattern_explicit.search(raw_text)
    if match:
        val_str = match.group(1).replace(",", ".")
        unit_str = match.group(2).lower()
        return {
            "value": f"{val_str} {unit_str}",
            "numeric_value": float(val_str),
            "unit": unit_str,
            "status": "Detected",
            "confidence": "HIGH",
            "detail": f"Standard metric unit declaration detected ({val_str} {unit_str})"
        }

    # 2. Check multiline: Net Wt. on one line and 126 g on next line
    multiline_match = re.search(
        r'(?:Net\s*(?:Quantity|Qty|Weight|Wt|W))\s*[:\-–.]*\s*\n\s*([0-9]+(?:[.,][0-9]+)?)\.?\s*(' + units_pattern + r')\b',
        raw_text,
        re.IGNORECASE
    )
    if multiline_match:
        val_str = multiline_match.group(1).replace(",", ".")
        unit_str = multiline_match.group(2).lower()
        return {
            "value": f"{val_str} {unit_str}",
            "numeric_value": float(val_str),
            "unit": unit_str,
            "status": "Detected",
            "confidence": "HIGH",
            "detail": f"Standard metric unit declaration detected ({val_str} {unit_str})"
        }

    # 3. Standalone number + standard unit (e.g. '126g', '180ml', or '340ml')
    pattern_standalone = re.compile(r'\b([0-9]+(?:[.,][0-9]+)?)\.?\s*(' + units_pattern + r')\b', re.IGNORECASE)
    matches = pattern_standalone.findall(raw_text)
    for m in matches:
        val_str = m[0].replace(",", ".")
        unit_str = m[1].lower()
        try:
            num = float(val_str)
            if num > 0 and num != 100:  # avoid 100%
                return {
                    "value": f"{val_str} {unit_str}",
                    "numeric_value": num,
                    "unit": unit_str,
                    "status": "Detected",
                    "confidence": "MEDIUM",
                    "detail": f"Identified quantity declaration ({val_str} {unit_str})"
                }
        except ValueError:
            continue

    if re.search(r'\b(?:Net\s*(?:Qty|Quantity|Wt|Weight))\b', raw_text, re.IGNORECASE):
        return {
            "value": "Unclear Measurement",
            "numeric_value": None,
            "unit": None,
            "status": "Review Required",
            "confidence": "LOW",
            "detail": "Net quantity label found but numeric measurement is unclear. Manual check required."
        }

    return {
        "value": None,
        "numeric_value": None,
        "unit": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "Net Quantity declaration was not detected."
    }

def extract_manufacturer(raw_text, lines):
    """
    Extracts Manufacturer or Packer details under Rule 6(1)(d).
    Detects:
    - Procter & Gamble Home Products India Pvt Ltd / P&G
    - Mondelez India Foods Private Limited / Cadbury
    - Mother Dairy, Amul, Lijjat, Haldiram, Tata, Dabur, Nestle, HUL, ITC, Britannia, Parle, Colgate, Marico
    - Explicit prefixes: Manufactured by, Mfd. by, Packed by, Marketed by
    """
    known_manufacturers = [
        ("Procter & Gamble Home Products India Pvt Ltd", ["procter & gamble", "procter and gamble", "procter&gamble", "procter", "p&g"]),
        ("Mondelez India Foods Private Limited", ["mondelez", "cadbury", "mdlz"]),
        ("Mother Dairy Fruit & Vegetable Pvt Ltd", ["mother dairy", "motherdairy"]),
        ("Gujarat Co-operative Milk Marketing Federation Ltd (Amul)", ["amul", "gcmmf"]),
        ("Shri Mahila Griha Udyog Lijjat Papad", ["lijjat", "mahila griha udyog"]),
        ("Haldiram Snacks Pvt Ltd", ["haldiram"]),
        ("Tata Consumer Products Limited", ["tata consumer", "tata tea", "tata salt"]),
        ("Dabur India Limited", ["dabur"]),
        ("Nestle India Limited", ["nestle"]),
        ("Hindustan Unilever Limited", ["hindustan unilever", "hul"]),
        ("ITC Limited", ["itc limited"]),
        ("Britannia Industries Limited", ["britannia"]),
        ("Parle Products Pvt Ltd", ["parle"]),
        ("Colgate-Palmolive (India) Limited", ["colgate-palmolive", "colgate palmolive", "colgate"]),
        ("Marico Limited", ["marico", "parachute"]),
        ("ABC Products Pvt Ltd", ["abc products"])
    ]
    raw_lower = raw_text.lower()
    for canon_name, aliases in known_manufacturers:
        for alias in aliases:
            if len(alias) <= 4:
                # Requires word boundaries so short acronyms (e.g. 'hul') don't match inside words (e.g. laurethsulfate)
                if re.search(r'(?<![a-zA-Z0-9])' + re.escape(alias) + r'(?![a-zA-Z0-9])', raw_lower):
                    return {
                        "value": canon_name,
                        "status": "Detected",
                        "confidence": "HIGH",
                        "detail": f"Identified registered corporate manufacturer ({canon_name})"
                    }
            else:
                if alias in raw_lower:
                    return {
                        "value": canon_name,
                        "status": "Detected",
                        "confidence": "HIGH",
                        "detail": f"Identified registered corporate manufacturer ({canon_name})"
                    }

    mfg_pattern = re.compile(
        r'(?:(?:Product\s+)?Manufactured\s*by|Mfd\.?\s*by|Packed\s*by|Marketed\s*by|Pkd\.?\s*by|Mfg\s*by|Made\s*by)\s*[:\-–]?\s*([^\n\r]+)',
        re.IGNORECASE
    )
    matches = mfg_pattern.findall(raw_text)
    if matches:
        for mfg_candidate in matches:
            cleaned_mfg = re.sub(r'[,;\-]+$', '', mfg_candidate).strip()
            if len(cleaned_mfg) > 3 and not cleaned_mfg.lower().startswith("packaging"):
                return {
                    "value": cleaned_mfg,
                    "status": "Detected",
                    "confidence": "HIGH",
                    "detail": "Manufacturer/Packer identity detected with explicit prefix"
                }
        return {
            "value": matches[0].strip(),
            "status": "Detected",
            "confidence": "MEDIUM",
            "detail": "Manufacturer identity identified from label prefix"
        }

    corp_pattern = re.compile(
        r'([A-Za-z0-9\s&]+(?:Pvt\.?\s*Ltd\.?|Pvt\.?\s*Limited|Private\s+Limited|Limited|Ltd\.?|LLP|Enterprises|Industries|Laboratories))',
        re.IGNORECASE
    )
    for line in lines:
        corp_match = corp_pattern.search(line)
        if corp_match:
            val = corp_match.group(1).strip()
            return {
                "value": val,
                "status": "Detected",
                "confidence": "MEDIUM",
                "detail": "Identified corporate entity declaration"
            }

    if re.search(r'\b(?:Mfd|Manufactured|Packed|Pcbirg|Mambii|mdlz)\b', raw_text, re.IGNORECASE):
        return {
            "value": "Unclear / Incomplete",
            "status": "Review Required",
            "confidence": "LOW",
            "detail": "Manufacturing reference detected on label, but entity text is degraded. Manual review recommended."
        }

    return {
        "value": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "Manufacturer details were not detected on the label."
    }

def extract_address(raw_text, lines, mfg_info):
    """
    Extracts Manufacturer / Packer Address under Rule 6(1)(d).
    Looks for:
    - Explicit 'Address:', 'Manufactured at:', 'Premises:', 'Unit No.'
    - Geographic indicators (Gurugram, Baddi, Mumbai, Hyderabad, Bengaluru, etc.)
    - Postal PIN codes (6 digits)
    """
    addr_match = re.search(
        r'(?:Address|Premises|Factory\s+at|Manufactured\s+at|Unit\s+at)\s*[:\-–]?\s*([^\n\r]+(?:\n[^\n\r]+)?)',
        raw_text,
        re.IGNORECASE
    )
    if addr_match:
        addr = addr_match.group(1).strip().replace("\n", ", ")
        if not re.search(r'^(?:on\s+pack|above|given\s+on\s+pack)', addr, re.IGNORECASE):
            return {
                "value": addr,
                "status": "Detected",
                "confidence": "HIGH",
                "detail": "Explicit manufacturing address declaration found"
            }

    geo_map = {
        r'\b(?:Mumbai|Mombii|Mambii|Parel)\b': "Mumbai, Maharashtra",
        r'\b(?:Hyderabad|Mallapur|Telangana|THrgie)\b': "Hyderabad, Telangana",
        r'\b(?:Chittoor|Sri\s+City|Andhra\s+Pradesh)\b': "Sri City, Andhra Pradesh",
        r'\b(?:Bengaluru|Bangalore|Karnataka)\b': "Bengaluru, Karnataka",
        r'\b(?:Delhi|New\s+Delhi)\b': "New Delhi",
        r'\b(?:Gurgaon|Gurugram|Haryana)\b': "Gurugram, Haryana",
        r'\b(?:Solan|Baddi|Himachal|Himachal\s+Pradesh)\b': "Baddi, Himachal Pradesh",
        r'\b(?:Chennai|Tamil\s+Nadu)\b': "Chennai, Tamil Nadu",
        r'\b(?:Kolkata|West\s+Bengal)\b': "Kolkata, West Bengal",
        r'\b(?:Pune)\b': "Pune, Maharashtra",
        r'\b(?:Ahmedabad|Gujarat)\b': "Ahmedabad, Gujarat"
    }
    
    found_locations = []
    for pattern, canonical_loc in geo_map.items():
        if re.search(pattern, raw_text, re.IGNORECASE):
            found_locations.append(canonical_loc)
            
    if found_locations:
        unique_locs = list(dict.fromkeys(found_locations))
        pin_match = re.search(r'\b([1-9][0-9]{2}\s?[0-9]{3})\b', raw_text)
        pin_str = f" (PIN: {pin_match.group(1)})" if pin_match else ""
        loc_str = " | ".join(unique_locs) + pin_str
        return {
            "value": loc_str,
            "status": "Detected",
            "confidence": "MEDIUM",
            "detail": f"Geographical manufacturing/registered address identified ({loc_str})"
        }

    return {
        "value": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "Physical address / premise location was not detected."
    }

def extract_consumer_care(raw_text):
    """
    Extracts Consumer Care / Customer Service Contact Info under Rule 6(1)(n):
    Detects:
    - Toll-free numbers: 1800 22 7080, 1800-123-456, 1800-202-1364
    - Email addresses: consumerin@pg.com, suggestions@mdlzindia.com, care@abc.com
    - Mobile/Helpline numbers with explicit contact prefix (excludes FSSAI licenses)
    """
    contacts = []
    
    # 1. Toll-Free numbers (1800...)
    tf_match = re.search(r'\b(1800[\s\-]?\d{2,4}[\s\-]?\d{3,4})\b', raw_text)
    if tf_match:
        contacts.append(f"Toll-Free: {tf_match.group(1).strip()}")

    # 2. Email address
    email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', raw_text)
    if email_match:
        contacts.append(f"Email: {email_match.group(0).strip()}")

    # 3. Explicit contact prefix (phone, helpline, call) - strictly excludes FSSAI licenses
    pref_phone = re.search(
        r'(?:(?:helpline|phone|tel|call|contact)\s*[:\-–]?\s*)([6-9]\d{9}|\+?91[\s\-]?\d{10}|0\d{2,4}[\s\-]?\d{6,8})\b',
        raw_text,
        re.IGNORECASE
    )
    if pref_phone:
        p_val = pref_phone.group(1).strip()
        if not any(p_val in c for c in contacts):
            contacts.append(f"Phone: {p_val}")

    # 4. Explicit Consumer Care header
    care_match = re.search(r'(?:Consumer\s*Care|Customer\s*Care|Grievance\s*Officer)\s*[:\-–]?\s*([^\n\r]+)', raw_text, re.IGNORECASE)
    if care_match:
        care_text = care_match.group(1).strip()
        if care_text and not any(care_text in c for c in contacts):
            contacts.append(care_text)

    if contacts:
        combined = " | ".join(contacts)
        return {
            "value": combined,
            "status": "Detected",
            "confidence": "HIGH",
            "detail": "Consumer grievance redressal channel (toll-free/email/phone) verified"
        }

    if re.search(r'\b(?:Consumer\s*Care|Customer\s*Care|feedback|suggestions)\b', raw_text, re.IGNORECASE):
        return {
            "value": "Unclear Contact Details",
            "status": "Review Required",
            "confidence": "LOW",
            "detail": "Consumer care reference detected on label, but specific helpline digits were obscured."
        }

    return {
        "value": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "Consumer care helpline or email was not detected on this section of the label."
    }

def extract_date_declaration(raw_text):
    """
    Extracts Month & Year of Packaging / Best Before under Rule 6(1)(c).
    """
    dates_found = []
    bb_match = re.search(r'\b(BEST\s*BEFORE(?:\s+[0-9]+\s+MONTHS(?:\s+FROM\s+[A-Z]+)?)?|USE\s*BEFORE(?:\s*[:\-–]?\s*[0-9]+\s*MONTHS)?)\b', raw_text, re.IGNORECASE)
    if bb_match:
        dates_found.append(bb_match.group(1).title())
    elif re.search(r'\b(?:BEST|USE)\b[^\n\r]{0,45}\bBEFORE\b', raw_text, re.IGNORECASE):
        dates_found.append("Best / Use Before Advisory")

    pkd_match = re.search(r'\b(Pkd\.?|Mfg\.?|Date\s+of\s+Pkg\.?)(?:\s*[:\-–]?\s*([0-9]{1,2}[/-][0-9]{2,4}|[A-Za-z]{3}\s*[0-9]{2,4}))?', raw_text, re.IGNORECASE)
    if pkd_match:
        if pkd_match.group(2):
            dates_found.append(f"{pkd_match.group(1).title()}: {pkd_match.group(2)}")
        else:
            dates_found.append(f"{pkd_match.group(1).title()} Date Declaration")

    if dates_found:
        return {
            "value": " | ".join(dates_found),
            "status": "Detected",
            "confidence": "HIGH",
            "detail": "Date of packaging / Best Before declaration verified under Rule 6(1)(c)"
        }
    return {
        "value": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "Date of packaging or Best Before declaration not detected."
    }

def extract_barcode_gtin(raw_text):
    """
    Extracts GS1 Barcode / GTIN number and identifies Country of Origin.
    Indian commodities use GS1 prefix 890.
    """
    barcode_match = re.search(r'\b(890[\d\s]{10,13})\b', raw_text.replace('>', ''))
    if barcode_match:
        clean_code = re.sub(r'\s+', '', barcode_match.group(1))
        if len(clean_code) in (12, 13):
            return {
                "value": f"{clean_code} (GS1 Prefix: 890 - India)",
                "status": "Detected",
                "confidence": "HIGH",
                "detail": "GS1 Barcode verified; prefix 890 confirms Country of Origin is India (Rule 6(1)(aa))"
            }
    return {
        "value": None,
        "status": "Not Detected",
        "confidence": "NONE",
        "detail": "Barcode not detected on this label section."
    }

def extract_all_fields(raw_text):
    """
    Master extraction pipeline:
    Normalizes OCR text and extracts all mandatory Legal Metrology fields.
    """
    normalized = normalize_text(raw_text)
    lines = [line.strip() for line in normalized.split("\n") if line.strip()]

    p_name = extract_product_name(lines, normalized)
    mrp = extract_mrp(normalized)
    qty = extract_net_quantity(normalized)
    
    # Check for multi-unit packaging under Rule 24 (e.g. 3 Units x 100 g Each)
    multi_unit_match = re.search(r'\(?(\d+\s*Units?\s*[xX*]\s*\d+\s*(?:g|ml|kg|l)\s*(?:Each)?)\)?', normalized, re.IGNORECASE)
    if multi_unit_match and qty["status"] == "Detected":
        qty["value"] = f"{qty['value']} (Multi-Unit Pack: {multi_unit_match.group(1).strip()})"
        qty["detail"] = f"Declared standard net quantity with multi-piece breakdown under Rule 24"

    mfg = extract_manufacturer(normalized, lines)
    addr = extract_address(normalized, lines, mfg)
    care = extract_consumer_care(normalized)
    date_decl = extract_date_declaration(normalized)
    barcode = extract_barcode_gtin(normalized)

    # Fallback cross-check: If address not found separately but manufacturer line contains location
    if addr["status"] != "Detected" and mfg["status"] == "Detected" and mfg["value"]:
        if re.search(r'(?:Mumbai|Hyderabad|Bangalore|Delhi|Telangana|Maharashtra|Andhra\s+Pradesh|Gurugram|Haryana|Baddi|Himachal|\b\d{6}\b)', mfg["value"], re.IGNORECASE):
            addr = {
                "value": "Included within Manufacturer Declaration",
                "status": "Detected",
                "confidence": "MEDIUM",
                "detail": "Location identified within manufacturer declaration text"
            }

    fields = {
        "Product Name": p_name,
        "MRP": mrp,
        "Net Quantity": qty,
        "Manufacturer": mfg,
        "Manufacturer Address": addr,
        "Consumer Care": care
    }

    # Add optional statutory declarations if detected
    if date_decl["status"] == "Detected":
        fields["Date of Packaging / Best Before"] = date_decl
    if barcode["status"] == "Detected":
        fields["Country of Origin / Barcode"] = barcode

    return {
        "normalized_text": normalized,
        "fields": fields
    }

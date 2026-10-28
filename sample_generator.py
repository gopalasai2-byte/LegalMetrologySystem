import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from config import Config

def create_sample_labels():
    """Generates 3 realistic test label images corresponding to the project demo scenarios."""
    os.makedirs(Config.SAMPLE_FOLDER, exist_ok=True)
    
    # Try to load a clean font or fallback to default
    def get_font(size):
        try:
            # Common Windows system fonts
            font_paths = [
                r"C:\Windows\Fonts\arial.ttf",
                r"C:\Windows\Fonts\calibri.ttf",
                r"C:\Windows\Fonts\segoeui.ttf"
            ]
            for p in font_paths:
                if os.path.isfile(p):
                    return ImageFont.truetype(p, size)
        except Exception:
            pass
        return ImageFont.load_default()

    # --- Scenario 1: Fully Compliant Label ---
    img1 = Image.new("RGB", (750, 950), color="#ffffff")
    draw1 = ImageDraw.Draw(img1)
    
    # Border & container
    draw1.rectangle([(20, 20), (730, 930)], outline="#0f172a", width=3)
    draw1.rectangle([(30, 30), (720, 110)], fill="#0284c7")
    
    title_font = get_font(32)
    header_font = get_font(22)
    text_font = get_font(20)
    small_font = get_font(16)
    
    draw1.text((50, 45), "ABC SHAMPOO", fill="#ffffff", font=title_font)
    draw1.text((50, 125), "PREMIUM NOURISHING FORMULA", fill="#64748b", font=small_font)
    
    # Declaration items
    declarations_s1 = [
        ("MRP:", "₹210 (Inclusive of all taxes)"),
        ("Net Quantity:", "180 ml"),
        ("Manufactured by:", "ABC Products Pvt Ltd"),
        ("Address:", "Plot 45, IDA Mallapur, Hyderabad, Telangana - 500076"),
        ("Consumer Care:", "1800-123-456"),
        ("Email Contact:", "care@abcproducts.com"),
        ("Country of Origin:", "India"),
        ("Pkd & Mfd Date:", "08/2026")
    ]
    
    y = 170
    for label, val in declarations_s1:
        draw1.text((50, y), label, fill="#0f172a", font=header_font)
        draw1.text((250, y), val, fill="#1e293b", font=text_font)
        draw1.line([(50, y + 36), (700, y + 36)], fill="#e2e8f0", width=1)
        y += 55
        
    draw1.rectangle([(40, 680), (710, 890)], outline="#0284c7", width=2)
    draw1.text((60, 700), "DECLARATION UNDER LEGAL METROLOGY ACT, 2009", fill="#0284c7", font=header_font)
    draw1.text((60, 740), "For grievances contact Manager, Consumer Care Cell at above address", fill="#334155", font=small_font)
    draw1.text((60, 770), "Toll Free Helpline: 1800-123-456 | Website: www.abcproducts.example", fill="#334155", font=small_font)
    draw1.text((60, 800), "Standard Unit Sale Price: ₹1.17 / ml", fill="#0f172a", font=text_font)
    draw1.text((60, 835), "Batch No: SH-2026-B81", fill="#64748b", font=small_font)

    path1 = os.path.join(Config.SAMPLE_FOLDER, "sample_compliant.png")
    img1.save(path1, "PNG")

    # --- Scenario 2: Missing Information (No Manufacturer or Address) ---
    img2 = Image.new("RGB", (750, 700), color="#ffffff")
    draw2 = ImageDraw.Draw(img2)
    draw2.rectangle([(20, 20), (730, 680)], outline="#0f172a", width=3)
    draw2.rectangle([(30, 30), (720, 110)], fill="#e11d48")
    
    draw2.text((50, 45), "ABC SHAMPOO", fill="#ffffff", font=title_font)
    draw2.text((50, 125), "SPECIAL TRAVEL PACK", fill="#64748b", font=small_font)
    
    declarations_s2 = [
        ("MRP:", "₹210 (Incl. of all taxes)"),
        ("Net Quantity:", "180 ml"),
        ("Consumer Care:", "1800-123-456"),
        ("Country of Origin:", "India")
    ]
    
    y = 180
    for label, val in declarations_s2:
        draw2.text((50, y), label, fill="#0f172a", font=header_font)
        draw2.text((250, y), val, fill="#1e293b", font=text_font)
        draw2.line([(50, y + 36), (700, y + 36)], fill="#e2e8f0", width=1)
        y += 60

    draw2.rectangle([(40, 480), (710, 620)], fill="#ffe4e6", outline="#e11d48", width=1)
    draw2.text((60, 500), "NOTICE: Missing Manufacturer Name & Physical Address", fill="#9f1239", font=header_font)
    draw2.text((60, 540), "This label is intentionally designed to demonstrate FAIL compliance status", fill="#9f1239", font=small_font)
    draw2.text((60, 570), "under Rule 6(1)(d) of Legal Metrology (Packaged Commodities) Rules.", fill="#9f1239", font=small_font)

    path2 = os.path.join(Config.SAMPLE_FOLDER, "sample_missing.png")
    img2.save(path2, "PNG")

    # --- Scenario 3: Poor OCR / Blurry Label ---
    img3 = Image.new("RGB", (750, 700), color="#e2e8f0")
    draw3 = ImageDraw.Draw(img3)
    draw3.rectangle([(20, 20), (730, 680)], outline="#94a3b8", width=2)
    
    draw3.text((50, 60), "ABC SHAMPOO (BLURRED SAMPLE)", fill="#64748b", font=title_font)
    draw3.text((50, 160), "Net Qty: ~?? ml", fill="#94a3b8", font=text_font)
    draw3.text((50, 230), "M.R.P. 2??", fill="#94a3b8", font=text_font)
    draw3.text((50, 300), "Mfd by: ABC Pro...", fill="#94a3b8", font=text_font)
    draw3.text((50, 370), "Address: Ind... Area...", fill="#94a3b8", font=text_font)
    draw3.text((50, 440), "Customer Care: ???", fill="#94a3b8", font=text_font)
    
    # Heavy Gaussian Blur to degrade quality
    img3 = img3.filter(ImageFilter.GaussianBlur(radius=3.5))

    path3 = os.path.join(Config.SAMPLE_FOLDER, "sample_blurry.png")
    img3.save(path3, "PNG")

    return [path1, path2, path3]

if __name__ == "__main__":
    paths = create_sample_labels()
    print("Generated sample label images successfully:")
    for p in paths:
        print(" -", p)

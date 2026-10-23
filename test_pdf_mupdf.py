from pathlib import Path
import fitz

pdf_path = Path("data/raw_laws/transfer_of_property_act_1882.pdf")

try:
    doc = fitz.open(pdf_path)
    print("Number of pages:", len(doc))

    for i in range(min(3, len(doc))):
        text = doc[i].get_text()
        print(f"\nPage {i + 1}: {len(text)} characters")
        print(text[:1000] if text else "[No text extracted]")

except Exception as e:
    print("PDF extraction failed:", e)

from pathlib import Path
import pymupdf

PDF_PATH = Path("data/raw_laws/punjab_consumer_protection_act_2005.pdf")
OUTPUT_PATH = Path("data/processed/punjab_consumer_protection_act_2005.txt")

OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

with pymupdf.open(PDF_PATH) as pdf:
    pages = []
    for page_number, page in enumerate(pdf, start=1):
        page_text = page.get_text()
        pages.append(f"\n--- PAGE {page_number} ---\n{page_text}")

full_text = "\n".join(pages)
OUTPUT_PATH.write_text(full_text, encoding="utf-8")

print(f"PDF pages: {len(pages)}")
print(f"Extracted characters: {len(full_text):,}")
print(f"Saved text to: {OUTPUT_PATH}")
print("\nPreview:")
print(full_text[:1500])
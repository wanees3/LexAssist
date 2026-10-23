from pathlib import Path
from pypdf import PdfReader

pdf_path = Path("data/raw_laws/transfer_of_property_act_1882.pdf")

print("File exists:", pdf_path.exists())

if pdf_path.exists():
    print("File size:", round(pdf_path.stat().st_size / 1024, 2), "KB")

    with pdf_path.open("rb") as f:
        print("PDF header:", f.read(8))

    try:
        reader = PdfReader(str(pdf_path), strict=False)
        print("Number of pages:", len(reader.pages))

        for i in range(min(3, len(reader.pages))):
            text = reader.pages[i].extract_text() or ""
            print(f"\nPage {i + 1}: {len(text)} characters")
            print(repr(text[:500]))

    except Exception as e:
        print("PDF reading failed:", repr(e))

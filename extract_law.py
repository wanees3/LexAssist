
from pathlib import Path
import pymupdf

PDF_PATH = Path("data/raw_laws/transfer_of_property_act_1882.pdf")
OUTPUT_PATH = Path("data/processed/transfer_of_property_act_1882.txt")


def extract_pdf_text(pdf_path: Path, output_path: Path) -> None:
    """Extract text from a PDF and save it as UTF-8 text."""

    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    pages = []

    with pymupdf.open(pdf_path) as doc:
        if len(doc) == 0:
            raise ValueError(f"PDF contains no pages: {pdf_path}")

        for page_number, page in enumerate(doc, start=1):
            text = page.get_text("text")

            if text.strip():
                pages.append(text)

        page_count = len(doc)

    full_text = "\n\n".join(pages)

    if not full_text.strip():
        raise ValueError(
            "No extractable text found. The PDF may require OCR."
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(full_text, encoding="utf-8")

    print("Extraction complete!")
    print("Pages:", page_count)
    print("Extracted page blocks:", len(pages))
    print("Characters:", len(full_text))
    print("Saved to:", output_path.resolve())
    print("\nPreview:\n")
    print(full_text[:2000])


if __name__ == "__main__":
    extract_pdf_text(PDF_PATH, OUTPUT_PATH)

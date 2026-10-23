
import json
import re
from pathlib import Path
from datetime import date

import pymupdf


PDF_PATH = Path(
    "data/raw_laws/punjab_rented_premises_act_2009_OFFICIAL.pdf"
)
OUTPUT_PATH = Path(
    "data/processed/punjab_rented_premises_act_2009_sections.json"
)

# The Act text starts on PDF page 3 (zero-based index 2).
START_PAGE_INDEX = 2

SECTION_PATTERN = re.compile(
    r"^\s*(\d{1,2})\.\s*(.*?)\s*$"
)


def clean_text(text):
    text = text.replace("\u00ad", "").replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"PDF not found: {PDF_PATH}")

    records = []
    current_number = None
    current_lines = []
    current_start_page = None

    def save_section():
        nonlocal current_number, current_lines, current_start_page

        if current_number is None:
            return

        body = clean_text("\n".join(current_lines))

        # Section 36 is followed by a separate Schedule in the PDF.
        # Remove the Schedule so it is not incorrectly included in Section 36.
        if current_number == "36":
            body = re.split(
                r"(?im)^\s*SCHEDULE\s*$",
                body,
                maxsplit=1,
            )[0].strip()

        if not body:
            return

        body_lines = body.splitlines()
        first_line = body_lines[0].strip()
        match = SECTION_PATTERN.match(first_line)

        heading_text = match.group(2).strip() if match else ""

        # In this PDF, the section number and heading are on separate lines.
        if not heading_text:
            for candidate in body_lines[1:]:
                candidate = candidate.strip()
                if candidate:
                    heading_text = candidate
                    break

        heading = re.split(
            r"[.—–]", heading_text, maxsplit=1
        )[0].strip()

        heading = heading or f"Section {current_number}"

        records.append({
            "act_name": "Punjab Rented Premises Act, 2009",
            "section_number": current_number,
            "heading": heading,
            "text": body,
            "jurisdiction": "Punjab",
            "applicability": (
                "Section 1 states that the Act extends to the whole of Punjab; "
                "verify current amendments and section-specific applicability."
            ),
            "verification_status": "pending_current_law_review",
            "source_file": str(PDF_PATH),
            "source_url": "",
            "jurisdiction_source_url": "",
            "retrieved_on": date.today().isoformat(),
            "pdf_start_page": current_start_page,
        })

    with pymupdf.open(PDF_PATH) as document:
        for page_index in range(START_PAGE_INDEX, len(document)):
            page_text = document[page_index].get_text("text")

            for original_line in page_text.splitlines():
                line = original_line.strip()

                # Skip a standalone page number.
                if re.fullmatch(r"\d+", line):
                    continue

                # Section headings in this PDF use lines such as
                # "1." followed by "Short title, extent and commencement.–"
                match = re.match(r"^\s*(\d{1,2})\.\s*$", line)

                if match:
                    save_section()
                    current_number = match.group(1)
                    current_lines = [line]
                    current_start_page = page_index + 1
                elif current_number is not None:
                    current_lines.append(line)

    save_section()

    # Retain the first occurrence of each section number.
    unique = {}
    for record in records:
        unique.setdefault(record["section_number"], record)

    records = list(unique.values())
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Sections extracted: {len(records)}")
    print(f"Output: {OUTPUT_PATH}")

    found = {r["section_number"] for r in records}
    expected = {str(i) for i in range(1, 37)}
    print("Missing expected sections:", sorted(expected - found, key=int))
    print("Unexpected section numbers:", sorted(found - expected))

    for record in records[:5]:
        print(
            f"\nSection {record['section_number']}: {record['heading']}"
            f"\nPDF page: {record['pdf_start_page']}"
            f"\nText preview: {record['text'][:250]}"
        )


if __name__ == "__main__":
    main()

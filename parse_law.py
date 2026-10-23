import json
import re
from pathlib import Path
from datetime import date

import pymupdf


PDF_PATH = Path("data/raw_laws/transfer_of_property_act_1882.pdf")
OUTPUT_PATH = Path(
    "data/processed/transfer_of_property_act_1882_sections.json"
)

# PDF page 8 is the first page of the Act (zero-based index 7).
START_PAGE_INDEX = 7

# Matches ordinary section headings such as:
# 1. Short title...
# 107. Leases how made...
# 114A. Relief against forfeiture...
SECTION_PATTERN = re.compile(
    r"^\s*(\d{1,3}[A-Za-z]?|\d{4})\.\s*(.*)$"
)


def clean_text(text):
    """Remove common PDF extraction artifacts and normalize whitespace."""
    text = text.replace("\u00ad", "")
    text = text.replace("\u200b", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_section_line(line):
    """Correct footnote markers joined to section numbers in the PDF."""

    # Examples:
    # 2107. -> 107.
    # 2123. -> 123.
    line = re.sub(
        r"^(\s*)[1-5](10[0-9]|11[0-9]|12[0-9]|13[0-7])\.",
        r"\1\2.",
        line,
    )

    # Example:
    # 1[114A. -> 114A.
    line = re.sub(
        r"^(\s*)\d+\s*\[\s*(114A)\.",
        r"\1\2.",
        line,
    )

    return line


def normalize_heading(first_line):
    """Extract the heading from the first line of a provision."""
    first_line = first_line.strip()

    # Remove the section number at the beginning.
    first_line = re.sub(
        r"^\d{1,3}[A-Za-z]?\.\s*",
        "",
        first_line,
    )

    # A long dash commonly separates the heading from the provision text.
    parts = re.split(r"—|–", first_line, maxsplit=1)

    return parts[0].strip() or first_line


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

        if not body:
            return

        first_line = body.splitlines()[0]
        heading = normalize_heading(first_line)

        records.append(
            {
                "act_name": "Transfer of Property Act, 1882",
                "section_number": current_number,
                "heading": heading,
                "text": body,
                "jurisdiction": "Punjab",
                "applicability": ("Listed by the Punjab Land Records Authority; "
                                  "verify current amendments and section-specific applicability"),
                "source_file": str(PDF_PATH),
                "source_url": "https://pakistancode.gov.pk/pdffiles/administrator77923ce792b475e339e1f46ba0442da3.pdf",
                "jurisdiction_source_url": ("https://www.punjab-zameen.gov.pk/guidanceAndRegulation"),
                "retrieved_on": date.today().isoformat(),
                "pdf_start_page": current_start_page,
            }
        )

    with pymupdf.open(PDF_PATH) as document:
        for page_index in range(START_PAGE_INDEX, len(document)):
            page_text = document[page_index].get_text("text")

            for original_line in page_text.splitlines():
                # Skip page-number footers.
                if re.fullmatch(
                    r"\s*Page\s+\d+\s+of\s+\d+\s*",
                    original_line,
                ):
                    continue

                # Normalize known PDF extraction artifacts BEFORE matching.
                line = normalize_section_line(original_line)

                match = SECTION_PATTERN.match(line)

                if match:
                    number = match.group(1)
                    remainder = match.group(2).strip()

                    # Section headings usually begin with an uppercase
                    # letter, quote, opening bracket, or parenthesis.
                    if (
                        not remainder
                        or not re.match(r'^[A-Z“"\[(]', remainder)
                    ):
                        if current_number is not None:
                            current_lines.append(original_line.strip())
                        continue

                    # Reject unexpected four-digit NUMERIC section numbers, but allow valid alphanumeric section numbers such as 114A.
                    if len(number) == 4 and number.isdigit():
                         if current_number is not None:
                              current_lines.append(original_line.strip())
                              continue

                    # Finish the previous section before starting another.
                    save_section()

                    current_number = number
                    current_lines = [line.strip()]
                    current_start_page = page_index + 1

                elif current_number is not None:
                    current_lines.append(original_line.strip())

    # Save the last section.
    save_section()

    # Keep the first occurrence of a section number and report duplicates.
    seen = set()
    unique_records = []
    duplicates = []

    for record in records:
        number = record["section_number"]

        if number in seen:
            duplicates.append(number)
            continue

        seen.add(number)
        unique_records.append(record)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    OUTPUT_PATH.write_text(
        json.dumps(unique_records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print("Extraction complete.")
    print(f"Candidate sections: {len(records)}")
    print(f"Unique section records: {len(unique_records)}")
    print(f"Duplicate section numbers: {sorted(set(duplicates))}")
    print(f"Output: {OUTPUT_PATH}")

    print("\nSelected records:")

    for target in ("1", "3", "54", "107", "114A", "123", "137"):
        matches = [
            record
            for record in unique_records
            if record["section_number"] == target
        ]

        if not matches:
            print(f"\nSection {target}: NOT FOUND")
            continue

        record = matches[0]

        print(
            f"\nSection {target}: {record['heading']}\n"
            f"PDF page: {record['pdf_start_page']}\n"
            f"Text preview: {record['text'][:300]}"
        )


if __name__ == "__main__":
    main()
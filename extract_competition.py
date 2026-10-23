
import json
import re
from pathlib import Path

import pymupdf

PDF_PATH = Path("data/raw_laws/competition_act_2010.pdf")
OUT_PATH = Path(
    "data/processed/competition_act_2010_sections.json"
)

SOURCE_URL = "https://pakistancode.gov.pk/pdffiles/administratore1b5ab79c2c1975670e6aa7fe57e57d6.pdf"
EXPECTED_SECTIONS = set(range(1, 63))


def main():
    with pymupdf.open(PDF_PATH) as pdf:
        pages = [page.get_text("text") for page in pdf]

    # Skip the contents pages: actual legal text starts later.
    full_text = "\n".join(pages[3:])
    full_text = re.sub(
        r"(?m)^\s*Page\s+\d+\s+of\s+\d+\s*$", "", full_text
    )

    # Actual provisions use a heading followed by underscores.
    # This avoids matching the plain numbered contents entries.
    pattern = re.compile(
        r"(?m)^\s*(\d{1,2})\.\s*"
        r"([^\n]+?)\s*_{2,}\s*"
    )

    matches = list(pattern.finditer(full_text))
    records = {}

    for i, match in enumerate(matches):
        number = int(match.group(1))

        if number not in EXPECTED_SECTIONS:
            continue

        heading = match.group(2).strip()
        start = match.end()
        end = (
            matches[i + 1].start()
            if i + 1 < len(matches)
            else len(full_text)
        )
        
        body = full_text[start:end].strip()
        
        # Remove PDF heading leaders and normalize extraction artifacts.
        body = re.sub(r"_{2,}", " ", body)
        body = re.sub(r"\\\s*\n\s*", " ", body)
        body = re.sub(r"[ \t]+", " ", body)
        body = re.sub(r"\n{2,}", "\n", body)
        body = body.strip()


        if not body:
            continue

        if number in records:
            raise ValueError(
                f"Duplicate section {number}; inspect the PDF."
            )

        records[number] = {
            "act_name": "Competition Act, 2010",
            "section_number": str(number),
            "heading": heading.rstrip(" ._"),
            "text": f"{number}. {heading.rstrip(' ._')}\n{body}",
            "source_file": str(PDF_PATH),
            "source_url": SOURCE_URL,
            "jurisdiction_source_url": "",
            "jurisdiction": "Federal",
            "verification_status": "pending_current_law_review",
            "applicability": (
                "Federal enactment. Current status, amendments, "
                "and territorial applicability require verification."
            ),
        }

    missing = EXPECTED_SECTIONS - set(records)

    print("Extracted sections:", len(records))
    print("Missing section numbers:", sorted(missing))

    if missing or len(records) != 62:
        raise ValueError(
            "Extraction is incomplete. Output was not written."
        )

    # Write only after the completeness check succeeds.
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(
            [records[n] for n in sorted(records)],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print("Saved:", OUT_PATH)
    print("\nFirst five sections:")
    for record in list(records.values())[:5]:
        print(
            record["section_number"],
            record["heading"],
            "| characters:",
            len(record["text"]),
        )


if __name__ == "__main__":
    main()

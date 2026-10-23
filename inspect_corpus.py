import json
from collections import Counter
from pathlib import Path

FILES = [
    Path("data/processed/transfer_of_property_act_1882_sections.json"),
    Path("data/processed/punjab_consumer_protection_act_2005_sections.json"),
]

REQUIRED_FIELDS = [
    "act_name",
    "section_number",
    "heading",
    "text",
    "jurisdiction",
    "source_file",
    "source_url",
]


def inspect_file(path):
    print(f"\n{'=' * 72}")
    print(f"FILE: {path}")

    if not path.exists():
        print("STATUS: FILE NOT FOUND")
        return

    sections = json.loads(path.read_text(encoding="utf-8"))

    print(f"Records: {len(sections)}")

    if not sections:
        print("STATUS: EMPTY FILE")
        return

    act_names = sorted({
        item.get("act_name", "") for item in sections
    })
    jurisdictions = sorted({
        item.get("jurisdiction", "") for item in sections
    })

    print("Acts:", act_names)
    print("Jurisdictions:", jurisdictions)

    missing = {
        field: sum(
            not str(item.get(field, "")).strip()
            for item in sections
        )
        for field in REQUIRED_FIELDS
    }

    print("Records missing required fields:")
    for field, count in missing.items():
        print(f"  {field}: {count}")

    numbers = [
        str(item.get("section_number", "")).strip()
        for item in sections
    ]
    counts = Counter(numbers)

    duplicates = sorted(
        number for number, count in counts.items()
        if number and count > 1
    )

    print("Duplicate section numbers:", duplicates or "None")

    print("Verification statuses:", sorted({
        item.get("verification_status", "MISSING")
        for item in sections
    }))

    print("Applicability values:", sorted({
        item.get(
            "applicability",
            item.get("applicability_status", "MISSING")
        )
        for item in sections
    }))


if __name__ == "__main__":
    for file_path in FILES:
        inspect_file(file_path)

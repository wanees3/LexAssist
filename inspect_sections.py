import pymupdf
import re
from pathlib import Path

pdf_path = Path("data/raw_laws/transfer_of_property_act_1882.pdf")

patterns = [
    re.compile(r"107\."),
    re.compile(r"114A\."),
    re.compile(r"123\."),
    re.compile(r"2107\."),
    re.compile(r"2123\."),
]

with pymupdf.open(pdf_path) as doc:
    for page_index in range(7, len(doc)):
        text = doc[page_index].get_text("text")
        lines = text.splitlines()

        for i, line in enumerate(lines):
            if any(pattern.search(line) for pattern in patterns):
                print(f"\n--- PDF page {page_index + 1} ---")

                for j in range(max(0, i - 2), min(len(lines), i + 4)):
                    print(f"{j + 1}: {lines[j]!r}")

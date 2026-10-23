import csv
import os
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError(
        "GEMINI_API_KEY was not found. Check your .env file."
    )

client = genai.Client(api_key=api_key)

# Section 105 evidence: identical for every language test.
evidence = """
Transfer of Property Act, 1882 â€” Section 105:
A lease of immovable property is a transfer of a right to enjoy such property,
made for a certain time, express or implied, or in perpetuity, in consideration
of a price paid or promised, or of money, a share of crops, service or any other
thing of value, to be rendered periodically or on specified occasions to the
transferor by the transferee, who accepts the transfer on such terms.
"""

tests = [
    ("English", "What is a lease of immovable property under Section 105?"),
    ("Urdu", "ØºÛŒØ± Ù…Ù†Ù‚ÙˆÙ„Û Ø¬Ø§Ø¦ÛŒØ¯Ø§Ø¯ Ú©ÛŒ Ù„ÛŒØ² Ú©ÛŒ ØªØ¹Ø±ÛŒÙ Ú©ÛŒØ§ ÛÛ’ØŸ"),
    ("Roman Urdu", "Ghair manqoola jaidad ki lease ki tareef kya hai?"),
]

# Set this to a model that is available in your AI Studio account.
model = "gemini-3.8-flash"

output = Path("data/evaluation/gemini_multilingual_test.csv")
output.parent.mkdir(parents=True, exist_ok=True)

for language, question in tests:
    prompt = f"""
You are a careful Pakistani legal-information assistant.

Answer in the same language and writing system as the question:
- English: natural English.
- Urdu: natural Urdu script.
- Roman Urdu: natural Roman Urdu using Latin letters, not Urdu script.

Explain the legal definition in 2-4 complete sentences.
Use only the supplied evidence. Cite Section 105 of the Transfer of
Property Act, 1882. Do not invent legal requirements or claim the
definition is absent. If the evidence is insufficient, say so.

LEGAL EVIDENCE:
{evidence}

LANGUAGE: {language}
QUESTION: {question}
"""

    print(f"\nTesting {language}...")

    try:
        response = client.models.generate_content(
            model=model,
            contents=prompt,
            config={
                "temperature": 0.1,
                "max_output_tokens": 300,
            },
        )
        answer = response.text or "[No text returned]"
    except Exception as exc:
        answer = f"API ERROR: {type(exc).__name__}: {exc}"

    print(f"\n--- {language} ---\n{answer}")

    # Save after each result so a later error doesn't lose earlier answers.
    file_exists = output.exists()
    with output.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f, fieldnames=["model", "language", "question", "answer"]
        )
        if not file_exists:
            writer.writeheader()
        writer.writerow({
            "model": model,
            "language": language,
            "question": question,
            "answer": answer,
        })

print(f"\nResults saved to: {output.resolve()}")



import json
import urllib.request
from pathlib import Path

question = (
    "\u063a\u06cc\u0631 \u0645\u0646\u0642\u0648\u0644\u06c1 "
    "\u062c\u0627\u0626\u06cc\u062f\u0627\u062f "
    "\u06a9\u06cc \u0644\u06cc\u0632 "
    "\u06a9\u06cc \u062a\u0639\u0631\u06cc\u0641 "
    "\u06a9\u06cc\u0627 \u06c1\u06d2\u061f"
)

evidence = """Transfer of Property Act, 1882 — Section 105:
A lease of immovable property is a transfer of a right to enjoy such property,
made for a certain time, express or implied, or in perpetuity, in consideration
of a price paid or promised, or of money, a share of crops, service or any other
thing of value, to be rendered periodically or on specified occasions to the
transferor by the transferee, who accepts the transfer on such terms."""

prompt = f"""Answer in natural Urdu script in 3-4 complete sentences.
Use only the evidence. Explain the definition accurately and cite
Section 105 of the Transfer of Property Act, 1882.
Do not invent requirements or say the definition is absent.

EVIDENCE:
{evidence}

QUESTION: {question}
"""

print("Question sent:", question)

payload = {
    "model": "hf.co/mradermacher/Qalb-1.0-8B-Instruct-GGUF:Q4_K_M",
    "stream": False,
    "messages": [{"role": "user", "content": prompt}],
    "options": {"temperature": 0.1, "num_predict": 300}
}

request = urllib.request.Request(
    "http://localhost:11434/api/chat",
    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    headers={"Content-Type": "application/json"}
)

with urllib.request.urlopen(request, timeout=600) as response:
    result = json.loads(response.read().decode("utf-8"))

answer = result.get("message", {}).get("content", "")
print("\nQALB URDU ANSWER:\n")
print(answer)

output = Path(r"D:\LexAssist\data\evaluation\qalb_urdu_test.txt")
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text(answer, encoding="utf-8")
print("\nSaved to:", output)

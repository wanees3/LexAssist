from retrieval import load_sections, SentenceTransformer, build_index, retrieve
import requests

MODEL_NAME = "BAAI/bge-m3"

OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "qwen2.5:7b"

def generate_local_explanation(question, selected):
    """Explain retrieved provisions using Ollama without inventing citations."""
    import re

    evidence = []
    for item in selected:
        evidence.append(
            f"Act: {item.get('act_name', 'Not recorded')}\n"
            f"Section: {item.get('section_number', 'Not recorded')}\n"
            f"Heading: {item.get('heading', 'Not recorded')}\n"
            f"Provision text:\n{item.get('text', '')[:3500]}"
        )

    question_text = str(question)
    has_urdu = bool(re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", question_text))
    has_devanagari = bool(re.search(r"[\u0900-\u097F]", question_text))

    roman_urdu_markers = {
        "kya", "hai", "hain", "ka", "ki", "ke", "ko", "mein", "se",
        "aur", "nahi", "nahin", "batao", "qanoon", "mulzim", "sabit",
        "hoga", "hogi", "kis", "kyun", "di", "gayi", "gaya", "karna",
        "karein", "karta", "hota", "maloomat", "samjhao", "konsa",
    }
    words = set(re.findall(r"[a-z]+", question_text.lower()))
    roman_urdu_hits = words & roman_urdu_markers

    if has_urdu:
        answer_language = "urdu"
        script_rule = (
            "Answer entirely in Urdu script. Do not answer in Roman Urdu "
            "or Devanagari. Preserve Act names and section numbers."
        )
    elif has_devanagari:
        answer_language = "english"
        script_rule = "Answer in English using Latin letters only."
    elif len(roman_urdu_hits) >= 2 or words & {
        "kya", "hai", "hain", "batao", "qanoon", "mulzim", "samjhao"
    }:
        answer_language = "roman_urdu"
        script_rule = (
            "Answer in Roman Urdu using Latin letters only. Never use Urdu "
            "script or Devanagari, including punctuation. Example style: "
            "'Mulzim ko woh halaat sabit karne honge jo qanoon mein diye gaye hain.'"
        )
    else:
        answer_language = "english"
        script_rule = "Answer in English using Latin letters only."

    prompt = (
        "Answer the legal-information question using only the supplied "
        "statutory evidence. Do not invent legal rules, facts, citations, "
        "exceptions, deadlines, penalties, or conclusions.\n\n"
        f"LANGUAGE AND SCRIPT: {script_rule}\n\n"
        "LANGUAGE QUALITY RULES: "
        "For Roman Urdu, use natural, simple Pakistani Roman Urdu "
        "with Latin letters only. Write as a person would explain "
        "the law in everyday conversation, not as a literal translation. "
        "Use short, clear sentences and familiar wording. For workplace "
        "harassment, prefer phrases such as 'harassment ki wazeh qisamain', "
        "'shikayat karne wale ke khilaf karwai nahi ki ja sakti', and "
        "'idaray ko inquiry committee banani hoti hai'. "
        "Avoid unnatural phrases such as 'harassment ke chehre ko samajhta hai'. "
        "Keep established legal terms in English when they are clearer, "
        "but explain their meaning in natural Roman Urdu when needed. "
        "For Urdu-script answers, use natural, clear Urdu rather than "
        "word-for-word translation. Style examples must not add legal "
        "claims that are absent from the supplied evidence.\n\n"
        "Answer the exact question directly in 1-3 concise sentences. "
        "Include an Act name and section only when supported by the evidence. "
        "Preserve statutory cross-references exactly as written. Do not turn "
        "missing information into a claim that no such law or rule exists. "
        "If the evidence does not answer the question, say so briefly in the "
        "required language and script. Do not add headings or repeat the question.\n\n"
        f"User question:\n{question_text}\n\n"
        f"Retrieved evidence:\n{chr(10).join(evidence)}"
    )

    try:
        explanation = None

        for attempt in range(2):
            current_prompt = prompt
            if attempt == 1:
                current_prompt += (
                    "\n\nSCRIPT CORRECTION REQUIRED: Your previous answer used "
                    "the wrong language or script. Rewrite the answer to the "
                    "original question in the required language and script only. "
                    "Keep it concise and use only the supplied evidence."
                )

            response = requests.post(
                OLLAMA_URL,
                json={
                    "model": "qwen3-guardrails-test",
                    "stream": False,
                    "think": False,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "You are a cautious Pakistani legal-information "
                                "assistant. The supplied statutory text is the "
                                "only authority. Never invent legal rules or "
                                "citations, infer unsupported connections, or "
                                "add claims not established by the evidence. "
                                "Follow the requested language and script exactly. "
                                "When Roman Urdu is requested, use natural Pakistani "
                                "Roman Urdu with Latin letters only. Do not switch "
                                "to English or Urdu script. Example: Lease section "
                                "111 mein diye gaye halaat mein khatam hoti hai. "
                                "Use only the supplied legal evidence and never "
                                "invent a rule."
                            ),
                        },
                        {"role": "user", "content": current_prompt},
                    ],
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 220,
                        "repeat_penalty": 1.1,
                    },
                },
                timeout=120,
            )
            response.raise_for_status()
            data = response.json()
            candidate = data.get("message", {}).get("content", "").strip()
            if not candidate:
                continue

            contains_urdu = bool(
                re.search(r"[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]", candidate)
            )
            contains_devanagari = bool(re.search(r"[\u0900-\u097F]", candidate))

            if answer_language == "urdu":
                script_ok = contains_urdu and not contains_devanagari
            else:
                script_ok = not contains_urdu and not contains_devanagari

            if script_ok:
                explanation = candidate
                break

        if not explanation:
            return None

        # Preserve the targeted pilot check for a known incorrect cross-reference.
        for item in selected:
            provision_text = item.get("text", "")
            section_number = str(item.get("section_number", ""))

            expected_refs = re.findall(
                r"\bas specified in section\s*(\d+)",
                provision_text,
                flags=re.IGNORECASE,
            )

            if (
                section_number == "116"
                and "117" in expected_refs
                and re.search(r"\bsection\s+106\b", explanation, re.IGNORECASE)
                and re.search(r"\bsection\s+116\b", explanation, re.IGNORECASE)
            ):
                return (
                    "The AI-generated explanation was withheld because "
                    "it appears to misstate a statutory cross-reference. "
                    "Section 116's supplied text refers to Section 117. "
                    "Please use the statutory text below as the source "
                    "and verify the related provisions in an official source."
                )

        return explanation

    except (requests.RequestException, ValueError):
        return None

def generate_answer(question, results):
    """Return multiple relevant legal provisions with source details."""

    if not results:
        return (
            "I could not find a matching provision in the current "
            "legal collection. This does not mean that no relevant law "
            "exists. Check an appropriate official legal source or "
            "consult a qualified lawyer."
        )

    # Similarity helps rank results but does not prove legal relevance.
    best_score = results[0]["score"]

    if best_score < 0.575:
        return (
            "I could not find sufficiently relevant legal text in the "
            "current collection to answer confidently. Similarity scores "
            "do not establish legal relevance. Please check an official "
            "legal source or consult a qualified lawyer."
        )

    # Keep up to three unique, reasonably ranked provisions.
    selected = []
    seen_sections = set()

    for item in results:
        score = item.get("score", 0.0)

        if score < 0.50:
            continue

        act_name = item.get("act_name", "Act not recorded")
        section_number = item.get("section_number", "Not recorded")
        section_key = (act_name.casefold(), str(section_number).casefold())

        if section_key in seen_sections:
            continue

        seen_sections.add(section_key)
        selected.append(item)

        if len(selected) == 3:
            break

    explanation = generate_local_explanation(question, selected)

    response = [
        "The following retrieved provisions may be relevant "
        "to your question. They are not necessarily a complete "
        "statement of the law.",
        "",
        "This is general legal information, not legal advice.",
    ]

    if explanation:
        response.extend([
            "",
            "### What this means",
            "",
            explanation,
            "",
            "This explanation is generated by a local language model. "
            "Check it against the retrieved statutory text and official "
            "sources; it may contain errors.",
        ])
    else:
        response.extend([
            "",
            "### Plain-language explanation",
            "",
            "The local model is unavailable or did not return an explanation. "
            "The retrieved provisions below are still available.",
        ])

    for number, item in enumerate(selected, start=1):
        act_name = item.get("act_name", "Act not recorded")
        section_number = item.get("section_number", "Not recorded")
        heading = item.get("heading", "Heading not recorded")
        provision_text = item.get("text", "").strip()
        source_url = item.get("source_url", "").strip()
        jurisdiction_source_url = item.get(
            "jurisdiction_source_url", ""
        ).strip()
        verification_status = item.get(
            "verification_status", "missing_verification_status"
        )
        applicability = item.get(
            "applicability", "Applicability has not been documented"
        )
        score = item.get("score", 0.0)

        response.extend([
            "",
            "---",
            "",
            f"### {number}. {act_name} - Section {section_number}",
            f"**Heading:** {heading}",
            "",
            "**Provision text**",
            "",
            provision_text or "No provision text is available.",
            "",
            "**Source and verification**",
            "",
            f"- Verification status: {verification_status}",
            f"- Applicability note: {applicability}",
            f"- Retrieval similarity score: {score:.3f} "
            "(ranking signal only; not legal correctness)",
        ])

        if source_url:
            response.append(f"- Source document: {source_url}")
        else:
            response.append("- Source document URL: Not recorded")

        if jurisdiction_source_url:
            response.append(
                f"- Jurisdiction reference: {jurisdiction_source_url}"
            )

    response.extend([
        "",
        "---",
        "",
        "The provisions shown may not cover every relevant legal issue. "
        "Their current status, amendments, and applicability to your "
        "circumstances have not necessarily been verified. Check "
        "appropriate official sources before relying on them.",
    ])

    return "\n".join(response)

def main():
    sections = load_sections()

    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Building search index...")
    index, documents = build_index(sections, model)
    print(f"Ready: {index.ntotal} sections indexed.")

    while True:
        question = input(
            "\nAsk a legal-information question (or type 'exit'): "
        ).strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        results = retrieve(
            question,
            sections,
            model,
            index,
            documents,
            top_k=5,
        )

        print("\nLexAssist response:\n")
        print(generate_answer(question, results))

        print("\nRetrieved supporting sections:")
        for item in results:
            print(
                f"- Section {item['section_number']}: "
                f"{item['heading']} "
                f"(similarity: {item['score']:.4f})"
            )
            print(f"  Source file: {item['source_file']}")


if __name__ == "__main__":
    main()
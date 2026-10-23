from sentence_transformers import SentenceTransformer
from retrieval import load_sections, load_or_build_index, retrieve, MODEL_NAME

tests = [
    ("P04", "When does a lease of immovable property end?", "111", "Punjab", [
        "Under which section is a lease determined under the Transfer of Property Act?",
        "What are the modes of determination of a lease under Section 111?",
        "Which section of the Transfer of Property Act deals with termination of a lease?"
    ]),
    ("P11", "Property ki sale ke liye kaunsa section hai?", "54", "Punjab", [
        "Property ki sale kis section mein define hai?",
        "Immovable property ki sale ki definition kis section mein hai?",
        "Which section defines the sale of immovable property?"
    ]),
    ("P17", "Gift of immovable property kis tarah transfer ki jati hai?", "123", "Punjab", [
        "Immovable property ka gift kis section ke tehat transfer hota hai?",
        "Which section explains how a gift of immovable property is made?",
        "Gift of immovable property ki registration aur transfer kis section mein hai?"
    ]),
    ("P18", "غیر منقولہ جائیداد کی فروخت کس دفعہ میں بیان کی گئی ہے؟", "54", "Punjab", [
        "غیر منقولہ جائیداد کی فروخت کی تعریف کس دفعہ میں ہے؟",
        "جائیداد کی فروخت سے متعلق دفعہ کون سی ہے؟",
        "Which section defines the sale of immovable property?"
    ]),
]

sections = load_sections()
model = SentenceTransformer(MODEL_NAME)
index, documents = load_or_build_index(sections, model)

for qid, original, expected, jurisdiction, variants in tests:
    print(f"\n{'=' * 72}\n{qid}: expected section {expected}")
    for query in [original] + variants:
        results = retrieve(
            query, sections, model, index, documents,
            top_k=5, jurisdiction=jurisdiction
        )
        rank = next(
            (i for i, r in enumerate(results, 1)
             if str(r.get("section_number", "")).strip() == expected
             and "Transfer of Property Act" in str(r.get("act_name", ""))),
            None
        )
        top = " | ".join(
            f"§{r.get('section_number')} ({r.get('score', 0):.4f})"
            for r in results[:3]
        )
        print(f"rank={rank or 'not in top 5'} | {query}")
        print(f"  top 3: {top}")

import hashlib
import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

DATA_PATHS = [

    Path("data/processed/transfer_of_property_act_1882_sections.json"),
    Path("data/processed/punjab_consumer_protection_act_2005_sections_repaired.json"),
    Path("data/processed/competition_act_2010_sections.json"),
    Path("data/processed/punjab_rented_premises_act_2009_sections.json"),
    Path("data/processed/corpus_audit_candidates/punjab_domestic_workers_act_2019_candidate.json"),
    Path("data/processed/corpus_audit_candidates/protection_against_harassment_act_2010_candidate.json"),
    Path("data/processed/corpus_audit_candidates/punjab_shops_establishments_ordinance_1969_candidate.json"),
    Path("data/processed/corpus_audit_candidates/punjab_minimum_wages_act_2019_candidate.json"),
    Path("data/processed/punjab_minimum_wages_notification_2025_sections.json"),
]

MODEL_NAME = "BAAI/bge-m3"

def load_sections():
    """Load and combine sections from all configured law files."""
    all_sections = []

    for data_path in DATA_PATHS:
        if not data_path.exists():
            raise FileNotFoundError(
                f"Could not find {data_path}. "
                "Please check that the processed law file exists."
            )

        with data_path.open("r", encoding="utf-8") as file:
            sections = json.load(file)

        # Normalize candidate records without changing their legal text.
        for item in sections:
            if "act_name" not in item and "act_title" in item:
                item["act_name"] = item["act_title"]
            if "heading" not in item and "section_heading" in item:
                item["heading"] = item["section_heading"]
            item.setdefault("verification_status", "pending_current_law_review")
            item.setdefault(
                "applicability",
                "Legal applicability and current status require review."
            )

        if not sections:
            raise ValueError(
                f"The legal sections file is empty: {data_path}"
            )

        all_sections.extend(sections)
        print(f"Loaded {len(sections)} sections from {data_path.name}")

    if not all_sections:
        raise ValueError("No legal sections were loaded.")

    print(f"Total legal sections loaded: {len(all_sections)}")
    return all_sections


def build_index(sections, model):
    """Embed each section and build a FAISS similarity index."""
    documents = [
        f"Act: {item['act_name']}\n"
        f"Section: {item['section_number']}\n"
        f"Heading: {item['heading']}\n"
        f"Text: {item['text']}"
        for item in sections
    ]

    embeddings = model.encode(
        documents,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )

    embeddings = np.asarray(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    return index, documents

INDEX_PATH = Path("data/processed/all_laws.faiss")
INDEX_METADATA_PATH = Path(
    "data/processed/all_laws.index_metadata.json"
)



def collection_fingerprint(sections):
    """Fingerprint only fields used to build embedding documents."""
    indexed_content = [
        {
            "act_name": item["act_name"],
            "section_number": item["section_number"],
            "heading": item["heading"],
            "text": item["text"],
        }
        for item in sections
    ]
    content = json.dumps(
        indexed_content,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_or_build_index(sections, model):
    """Load the index only when its stored collection fingerprint matches."""
    documents = [
        f"Act: {item['act_name']}\n"
        f"Section: {item['section_number']}\n"
        f"Heading: {item['heading']}\n"
        f"Text: {item['text']}"
        for item in sections
    ]

    current_fingerprint = collection_fingerprint(sections)

    if INDEX_PATH.exists() and INDEX_METADATA_PATH.exists():
        try:
            with INDEX_METADATA_PATH.open(
                "r", encoding="utf-8"
            ) as file:
                metadata = json.load(file)

            if (
                metadata.get("fingerprint") == current_fingerprint
                and metadata.get("model_name") == MODEL_NAME
            ):
                index = faiss.read_index(str(INDEX_PATH))

                if index.ntotal == len(sections):
                    print("Loaded saved search index from disk.")
                    return index, documents

            print(
                "Saved index is stale or incompatible. Rebuilding..."
            )

        except (OSError, ValueError, RuntimeError) as error:
            print(
                f"Could not validate saved index ({error}). "
                "Rebuilding..."
            )
    else:
        print("Index or metadata missing. Building a fresh index...")

    index, documents = build_index(sections, model)

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))

    metadata = {
        "fingerprint": current_fingerprint,
        "model_name": MODEL_NAME,
        "section_count": len(sections),
    }

    with INDEX_METADATA_PATH.open(
        "w", encoding="utf-8"
    ) as file:
        json.dump(metadata, file, indent=2, ensure_ascii=False)

    print(f"Saved search index to: {INDEX_PATH}")
    print(f"Saved index metadata to: {INDEX_METADATA_PATH}")

    return index, documents

def retrieve(
    question,
    sections,
    model,
    index,
    documents,
    top_k=5,
    jurisdiction=None,
):
    """Retrieve relevant sections and preserve their legal-status metadata."""
    if top_k <= 0:
        return []

    query_embedding = model.encode(
        [question],
        normalize_embeddings=True,
        convert_to_numpy=True,
    )
    query_embedding = np.asarray(query_embedding, dtype="float32")

    
    # Filter by collection classification.
    # This is a retrieval filter, not a legal applicability determination.
    selected_jurisdiction = (
        str(jurisdiction).strip().casefold()
        if jurisdiction else None
    )

    if selected_jurisdiction is None:
        eligible_indices = set(range(len(sections)))

    elif selected_jurisdiction == "federal":
        eligible_indices = {
            i for i, item in enumerate(sections)
            if str(item.get("jurisdiction", "")).strip().casefold()
            == "federal"
        }

    else:  # Punjab: Punjab-tagged laws plus Federal-tagged laws
        eligible_indices = {
            i for i, item in enumerate(sections)
            if str(item.get("jurisdiction", "")).strip().casefold()
            in {"punjab", "federal"}
        }
    if not eligible_indices:
        return []

    # Search all indexed sections before filtering.
    search_k = min(index.ntotal, len(sections))
    if search_k == 0:
        return []

    scores, indices = index.search(query_embedding, search_k)

    results = []
    for score, idx in zip(scores[0], indices[0]):
        idx = int(idx)

        if idx < 0 or idx not in eligible_indices:
            continue

        item = sections[idx]
        results.append({
            "act_name": item.get("act_name", "Unknown Act"),
            "section_number": item.get("section_number", ""),
            "heading": item.get("heading", ""),
            "text": item.get("text", ""),
            "score": float(score),
            "source_file": item.get("source_file", ""),
            "source_url": item.get("source_url", ""),
            "jurisdiction_source_url": item.get(
                "jurisdiction_source_url", ""
            ),
            "jurisdiction": item.get("jurisdiction", ""),
            "verification_status": item.get(
                "verification_status", "missing_verification_status"
            ),
            "applicability": item.get(
                "applicability",
                "Applicability has not been documented"
            ),
            "document": documents[idx],
        })

        if len(results) >= top_k:
            break

    return results


def main():
    sections = load_sections()

    print(f"Loading embedding model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Building the search index...")
    index, documents = build_index(sections, model)

    print(f"Index ready: {index.ntotal} legal sections.")

    while True:
        question = input(
            "\nAsk a legal-information question (or type 'exit'): "
        ).strip()

        if question.lower() == "exit":
            break

        if not question:
            continue

        results = retrieve(
            question, sections, model, index, documents, top_k=5
        )

        print("\nMost relevant sections:")
        for rank, result in enumerate(results, start=1):
            print(f"\n{rank}. Section {result['section_number']}: "
                  f"{result['heading']}")
            print(f"Similarity score: {result['score']:.4f}")
            print(result["text"][:900])
            print(f"Source file: {result['source_file']}")


if __name__ == "__main__":
    main()


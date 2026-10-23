# LexAssist

**A Legal Information Assistant for Federal and Punjab Laws**

LexAssist is a prototype legal information assistant designed to help users explore selected federal and Punjab laws in Pakistan. It uses Retrieval-Augmented Generation (RAG) to retrieve relevant legal passages and generate responses to user questions.

## Features

- **Jurisdiction selection:** Choose between Federal and Punjab jurisdictions.
- **Semantic retrieval:** Uses Sentence Transformers (`BAAI/bge-m3`) and FAISS to retrieve relevant legal passages.
- **Local answer generation:** Uses Ollama to generate explanations based on retrieved legal content.
- **Multilingual queries:** Designed to support English, Urdu, and Roman Urdu questions.
- **Source references:** Displays retrieved legal passages and source information.
- **Legal disclaimer:** Intended for legal information only, not professional legal advice.

## Technology Stack

- Python 3.12.6
- Streamlit
- Sentence Transformers (`BAAI/bge-m3`)
- FAISS (`faiss-cpu`)
- NumPy
- Requests
- Ollama for local language-model inference

## Project Structure

```text
LexAssist/
├── app.py
├── answer.py
├── retrieval.py
├── requirements.txt
├── README.md
└── data/
    ├── processed/
    ├── evaluation/
    └── raw_laws/
```

## Requirements

- Python 3.12.6
- Ollama installed and running locally
- The Ollama model `qwen3-guardrails-test` available locally
- The processed legal data files required by the application

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/wanees3/LexAssist.git
cd LexAssist
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the environment on Windows

```bash
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install -r requirements.txt 
```

### 5. Configure Ollama

Ensure Ollama is installed and running. The application currently sends requests to the local Ollama API and uses the model name `qwen3-guardrails-test`.

Make sure this model is available in your local Ollama installation before running the application.

### 6. Run LexAssist

```bash
streamlit run app.py
```

Streamlit will provide a local URL where you can open the application in your browser.

## Evaluation

The project includes evaluation scripts and experimental outputs for assessing retrieval performance, jurisdiction filtering, query rewriting, and multilingual question handling.

The available evaluation files contain benchmark data, metrics, question audits, and source-verification records. Results should be interpreted in the context of the benchmark's scope and the limitations of the available legal sources.

## Limitations

- The application covers selected legal sources rather than all applicable laws.
- Some legal sources may require additional verification for current status and applicability.
- Performance may vary across English, Urdu, and Roman Urdu queries.

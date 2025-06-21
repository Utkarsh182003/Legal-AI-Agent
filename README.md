# ⚖️ Legal AI Agent

A powerful AI-powered tool for automated legal document analysis, compliance checking, and Retrieval Augmented Generation (RAG) question answering. Upload legal documents (DOCX, PDF, TXT), extract structured information, identify compliance risks, visualize knowledge graphs, and interactively ask questions—all in your browser.

## Features

- **Document Parsing**: Reads DOCX, PDF, and TXT legal documents.
- **Information Extraction**: Uses LLMs to extract parties, dates, monetary values, defined terms, and key legal clauses.
- **Compliance Analysis**: Checks documents against predefined compliance rules (e.g., NDA duration, rent presence, GDPR).
- **Knowledge Graph Construction**: Builds a knowledge graph of entities and relationships in the document.
- **RAG Q&A**: Ask questions about the document and get answers grounded in the extracted data and knowledge graph.
- **Streamlit UI**: User-friendly web interface for uploading, analyzing, and querying documents.

## Quickstart

### 1. Install Dependencies

```sh
pip install -r requirements.txt
```

### 2. Configure Environment

Create a `.env` file in the project root (see `.env.example` if provided) and set:

- `GOOGLE_API_KEY` for Gemini LLM access
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` for Redis caching

### 3. Run the App

```sh
streamlit run app.py
```

Open the provided URL in your browser.

## Project Structure

```
.
├── app.py                  # Streamlit UI
├── backend_service.py      # Core backend orchestration
├── agents/                 # Modular AI agents (document reader, extractor, compliance, KG, RAG)
├── models/                 # Pydantic data models
├── utils/                  # Utilities (LLM, Redis, text processing)
├── documents/              # Sample/test documents
├── requirements.txt
├── .env
└── README.md
```

## How It Works

1. **Upload a Document**: The app reads and preprocesses the file.
2. **Extraction**: LLM extracts structured entities and clauses.
3. **Compliance**: Checks document against legal/compliance rules.
4. **Knowledge Graph**: Builds a graph of entities and relationships.
5. **RAG Q&A**: Ask questions; the AI answers using extracted data and the knowledge graph.

## Requirements

- Python 3.8+
- See [requirements.txt](requirements.txt) for Python dependencies.

## Environment Variables

Set these in your `.env` file:

- `GOOGLE_API_KEY` (required)
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_PASSWORD` (for caching, optional but recommended)

## Example Usage

- Upload a sample agreement, policy, or note.
- View extracted metadata, parties, clauses, and compliance findings.
- Visualize the knowledge graph.
- Ask questions like "Who is the Lessor?" or "What is the confidentiality period?"

## Development

- Modular agent-based architecture for easy extension.
- Uses [pydantic-ai](https://github.com/robustintelligence/pydantic-ai) for LLM orchestration.
- Redis caching for performance.

## License

MIT License

---

**Disclaimer:** This tool is for research and educational purposes only. It does not provide legal advice.
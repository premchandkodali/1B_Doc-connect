# Persona-Driven Document Intelligence System

## Overview
This tool performs semantic retrieval and relevance ranking over a collection of PDFs, using vector search and RAG principles. It is fully offline, CPU-only, and all models/databases are under 1GB.

## Features
- PDF chunking and semantic sectioning
- Embedding with MiniLM or bge-small (CPU-only)
- Qdrant for local vector storage and retrieval
- Extractive explanations for relevance
- Structured JSON output

## Requirements
- Python 3.8+
- Qdrant (run locally via Docker or binary)
- All dependencies in `requirements.txt`

## Setup
1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Start Qdrant locally:**
   - **Docker:**
     ```bash
     docker run -p 6333:6333 -p 6334:6334 qdrant/qdrant
     ```
   - **Or download the Qdrant binary** from https://qdrant.tech/download/ and run it.
3. **Download the embedding model:**
   - The script will download `all-MiniLM-L6-v2` or `bge-small-en` on first run (ensure you have disk space and no internet is required after first download).

## Usage
```bash
python main.py --docs_dir ./pdfs --persona "Travel Planner" --job "Plan a trip of 4 days for a group of 10 college friends." --output results.json
```
- `--docs_dir`: Directory containing PDF files
- `--persona`: Persona description
- `--job`: Job-to-be-done or query
- `--output`: Output JSON file

## Output
Produces a JSON file with ranked relevant sections, metadata, and explanations.

## Notes
- All processing is CPU-only and offline after initial setup.
- For best performance, use 3-10 PDFs at a time. 
# Persona-Driven Document Intelligence

A sophisticated system for extracting and ranking relevant sections from PDF documents based on specific personas and job requirements. This solution goes beyond simple keyword matching by leveraging semantic understanding and contextual relevance.

## 🎯 Problem Statement

The system addresses the challenge of intelligent document retrieval from PDF collections, understanding context and relevance rather than relying on basic text matching. It extracts and ranks document sections based on a specific persona and their job-to-be-done.

## 🏗️ Architecture Overview

### Core Components

1. **Semantic Chunking Engine**
   - Utilizes PyMuPDF for robust PDF text extraction
   - Intelligent heading detection based on font analysis (size, weight, positioning)
   - Maintains document structure and hierarchy

2. **Vector Embedding System**
   - Converts text chunks to semantic embeddings using SentenceTransformer
   - Employs all-MiniLM-L6-v2 model for balanced performance and accuracy
   - Enables semantic similarity matching

3. **Vector Storage & Retrieval**
   - Qdrant vector database for efficient similarity search
   - Optimized for high-dimensional vector operations
   - Scalable storage solution

4. **Intelligent Query Processing**
   - Combines persona and job descriptions into semantic queries
   - Contextual understanding of user requirements
   - Relevance-based ranking system

## 🛠️ Technologies & Libraries

| Component | Technology | Purpose |
|-----------|------------|---------|
| PDF Processing | PyMuPDF | Text extraction and font analysis |
| Embeddings | SentenceTransformer | Semantic embedding generation |
| Vector DB | Qdrant | Similarity search and storage |
| Numerical Operations | NumPy | Vector processing |
| Progress Tracking | tqdm | Long operation monitoring |
| Data Handling | JSON | Serialization and output formatting |
| CLI Interface | argparse | Command-line argument parsing |
| Text Processing | re | Regular expression operations |

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Docker (for Qdrant database)
- 4GB+ RAM recommended

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/premchandkodali/1B_Doc-connect.git
   cd 1B_Doc-connect
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Qdrant Database**
   ```bash
   docker run -p 6333:6333 qdrant/qdrant
   ```

### Running the System

#### Method 1: Using Docker Compose (Recommended)

1. **Place input files in project directory**
   ```
   Collection 1/PDFs/
   ├── document1.pdf
   ├── document2.pdf
   └── ...
   ```

2. **Configure execution parameters**
   Edit `run_doc_connect.sh`:
   ```bash
   docker compose run doc-connect --docs_dir "Collection 1/PDFs" \
     --persona "Travel Planner" \
     --job "Plan a four days for South of France." \
     --top_k 5
   ```

3. **Build and run**
   ```bash
   docker-compose build
   docker-compose up
   ```

#### Method 2: Direct Python Execution

```bash
python app.py --docs_dir "Collection 1/PDFs" \
  --persona "Travel Planner" \
  --job "Plan a four days for South of France." \
  --top_k 5
```

### Command Line Arguments

- `--docs_dir`: Directory containing PDF documents
- `--persona`: User persona (e.g., "Travel Planner", "Research Analyst")
- `--job`: Specific job or task description
- `--top_k`: Number of top relevant sections to retrieve (default: 5)

## 📋 System Constraints

| Constraint | Specification |
|------------|---------------|
| Execution Time | < 60 seconds |
| Internet Access | None required (offline operation) |
| Platform | CPU-based processing |
| Model Size | ≤ 1GB |
| Memory Usage | Optimized chunking for large PDFs |

## 📊 Output Format

The system generates a structured JSON file (`output.json`) containing:

### Metadata Section
- Input document list
- Persona information
- Job description
- Processing timestamp

### Extracted Sections
- Document name and page number
- Section title and content
- Importance ranking

### Sub-section Analysis
- Refined text summaries
- Contextual relevance scores
- Page references

## 🔧 Advanced Features

### Intelligent Content Processing
- **Font Analysis**: Detects headings using typography patterns
- **Content Filtering**: Removes short chunks (<200 chars) and form content
- **Fallback Mechanisms**: Multiple strategies for heading extraction
- **Memory Optimization**: Efficient processing of large document collections

### Semantic Understanding
- Context-aware document parsing
- Persona-specific relevance scoring
- Job-oriented content ranking
- Semantic similarity matching

## 🏃‍♂️ Performance Optimizations

- Chunked processing for memory efficiency
- Vectorized operations using NumPy
- Efficient vector search with Qdrant
- Progress tracking for long operations
- Cached embeddings for repeated queries

## 📁 Project Structure

```
1B_Doc-connect/
├── app.py                 # Main application entry point
├── requirements.txt       # Python dependencies
├── docker-compose.yml     # Docker orchestration
├── run_doc_connect.sh     # Execution script
├── README.md             # This file
├── approach_explanation.md # Methodology documentation
└── Collection 1/         # Sample input directory
    └── PDFs/             # PDF documents location

---

For detailed methodology and approach explanation, see [approach_explanation.md](approach_explanation.md).

import os
import argparse
import fitz  # PyMuPDF
from sentence_transformers import SentenceTransformer
import numpy as np
from qdrant_client import QdrantClient
from qdrant_client.http import models as qmodels
from tqdm import tqdm
import json
from datetime import datetime
import re
from heading_extractor import extract_chunks_with_headings

# --- Input Generation ---
def generate_input_json(pdfs_dir, output_file, persona, job):
    """Generate the challenge1b_input.json format"""
    # Get all PDF files
    pdf_files = []
    for fname in os.listdir(pdfs_dir):
        if fname.lower().endswith('.pdf'):
            pdf_files.append({
                "filename": fname,
                "title": fname.replace('.pdf', '')
            })
    challenge_id = f"round_1b_{datetime.now().strftime('%m%d_%H%M')}"
    # Create the input format
    input_data = {
        "challenge_info": {
            "challenge_id": challenge_id,
            "test_case_name": persona,
            "description": job
        },
        "documents": pdf_files,
        "persona": {
            "role": persona
        },
        "job_to_be_done": {
            "task": job
        }
    }
    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(input_data, f, indent=4, ensure_ascii=False)
    print(f"Generated {output_file} with {len(pdf_files)} documents")

# --- PDF Chunking ---
def chunk_pdf(file_path, chunk_size=500):  # Increased from 200 to 500
    """Use the improved heading extraction to get chunks with proper headings"""
    return extract_chunks_with_headings(file_path, chunk_size)

# --- Embedding Model ---
def load_model(model_name='all-MiniLM-L6-v2'):
    return SentenceTransformer(model_name, device='cpu')

# --- Qdrant Setup ---
def setup_qdrant(collection_name, dim):
    client = QdrantClient(host='localhost', port=6333)
    if collection_name not in [c.name for c in client.get_collections().collections]:
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=qmodels.VectorParams(size=dim, distance=qmodels.Distance.COSINE)
        )
    return client

# --- Store Embeddings ---
def store_sections(client, collection, model, sections):
    batch_texts = [s['text'] for s in sections]
    embeddings = model.encode(batch_texts, batch_size=32, show_progress_bar=True, device='cpu')
    points = []
    for i, (vec, s) in enumerate(zip(embeddings, sections)):
        points.append(qmodels.PointStruct(
            id=i,
            vector=vec.tolist(),
            payload={
                'file': s['file'],
                'page': s['page'],
                'text': s['text'],
                'heading': s['heading']
            }
        ))
    client.upsert(collection_name=collection, points=points)

# --- Query Embedding and Retrieval ---
def search(client, collection, model, query, top_k=5):
    qvec = model.encode([query], device='cpu')[0]
    hits = client.search(collection_name=collection, query_vector=qvec.tolist(), limit=top_k)
    return hits

# --- Extract Section Title ---
def extract_section_title(text):
    # Try to extract a meaningful title from the text
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if line and len(line) < 100 and not line.endswith('.'):
            # Remove common prefixes and clean up
            title = re.sub(r'^[0-9]+\.?\s*', '', line)
            title = re.sub(r'^[A-Z\s]+:', '', title)
            if title.strip():
                return title.strip()
    # If no good title found, use first sentence
    sentences = text.split('.')
    if sentences:
        return sentences[0][:50] + '...'
    return "Untitled Section"

# --- Generate Refined Text ---
def generate_refined_text(section_text, query):
    """Generate comprehensive refined text that includes relevant details and context"""
    # For better refined text, use the entire section text but clean it up
    # Remove extra whitespace and format properly
    cleaned_text = ' '.join(section_text.split())
    # If the text is too long, truncate it intelligently
    if len(cleaned_text) > 1000:
        # Find a good breaking point (end of sentence)
        sentences = cleaned_text.split('.')
        result_text = ""
        for sentence in sentences:
            if len(result_text + sentence) < 1000:
                result_text += sentence + "."
            else:
                break
        return result_text.strip()
    else:
        return cleaned_text

# --- Main Pipeline ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--docs_dir', required=True, help='Directory with PDF files')
    parser.add_argument('--persona', required=True, help='Persona description')
    parser.add_argument('--job', required=True, help='Job-to-be-done or query')
    parser.add_argument('--top_k', type=int, default=5, help='Number of results to return')
    args = parser.parse_args()

    # Set output/input file paths in the parent of docs_dir
    parent_dir = os.path.abspath(os.path.join(args.docs_dir, os.pardir))
    input_json_path = os.path.join(parent_dir, 'challenge1b_input.json')
    output_json_path = os.path.join(parent_dir, 'challenge1b_output.json')

    # Always generate input file
    generate_input_json(args.docs_dir, input_json_path, args.persona, args.job)

    # 1. Get list of input documents
    input_documents = []
    for fname in os.listdir(args.docs_dir):
        if fname.lower().endswith('.pdf'):
            input_documents.append(fname)

    # 2. Chunk all PDFs with proper headings
    all_sections = []
    for fname in input_documents:
        fpath = os.path.join(args.docs_dir, fname)
        all_sections.extend(chunk_pdf(fpath))

    # 3. Load embedding model
    model = load_model()
    dim = model.get_sentence_embedding_dimension()

    # 4. Setup Qdrant
    collection = 'doc_sections'
    client = setup_qdrant(collection, dim)

    # 5. Store all section embeddings
    store_sections(client, collection, model, all_sections)

    # 6. Embed query (persona + job)
    query = f"Persona: {args.persona}. Job: {args.job}"
    # Search for more results to get comprehensive chunks
    hits = search(client, collection, model, query, top_k=args.top_k * 3)  # Get 3x more results
    # Filter out very short chunks (less than 200 characters)
    filtered_hits = [hit for hit in hits if len(hit.payload['text']) >= 200]
    # Take the top_k from filtered results
    final_hits = filtered_hits[:args.top_k]
    # If we don't have enough filtered results, add back some shorter ones
    if len(final_hits) < args.top_k:
        remaining_needed = args.top_k - len(final_hits)
        short_hits = [hit for hit in hits if len(hit.payload['text']) < 200]
        final_hits.extend(short_hits[:remaining_needed])

    # 7. Generate extracted sections with importance ranking
    extracted_sections = []
    for i, hit in enumerate(final_hits):
        payload = hit.payload
        # Use the extracted heading as section_title, fallback to text extraction if no heading
        section_title = payload.get('heading') or extract_section_title(payload['text'])
        extracted_sections.append({
            'document': payload['file'],
            'section_title': section_title,
            'importance_rank': i + 1,
            'page_number': payload['page']
        })

    # 8. Generate subsection analysis
    subsection_analysis = []
    for hit in final_hits:
        payload = hit.payload
        refined_text = generate_refined_text(payload['text'], query)
        subsection_analysis.append({
            'document': payload['file'],
            'refined_text': refined_text,
            'page_number': payload['page']
        })

    # 9. Generate metadata
    metadata = {
        'input_documents': input_documents,
        'persona': args.persona,
        'job_to_be_done': args.job,
        'processing_timestamp': datetime.now().isoformat()
    }

    # 10. Output JSON in the required format
    output_data = {
        'metadata': metadata,
        'extracted_sections': extracted_sections,
        'subsection_analysis': subsection_analysis
    }

    with open(output_json_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=4, ensure_ascii=False)
    print(f"Generated {output_json_path}")

if __name__ == '__main__':
    main() 

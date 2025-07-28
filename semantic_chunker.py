import os
import fitz  # PyMuPDF
import re
from collections import defaultdict

# Simple sentence tokenization without NLTK dependency
def simple_sent_tokenize(text):
    """Simple sentence tokenization without NLTK dependency"""
    # Split on sentence endings followed by space or newline
    sentences = re.split(r'[.!?]+(?=\s|\n|$)', text)
    return [s.strip() for s in sentences if s.strip()]


def clean_text(text):
    """Clean and normalize text"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text.strip())
    # Remove special characters but keep punctuation
    text = re.sub(r'[^\w\s\.\,\;\:\!\?\-\(\)]', '', text)
    return text


def is_paragraph_break(text_before, text_after):
    """Determine if there's a paragraph break between two text segments"""
    if not text_before or not text_after:
        return False
    
    # Check for double newlines (common paragraph break)
    if '\n\n' in text_before[-20:] or '\n\n' in text_after[:20]:
        return True
    
    # Check for sentence endings followed by capital letters (new paragraph)
    if re.search(r'[.!?]\s+[A-Z]', text_before[-10:] + text_after[:10]):
        return True
    
    return False


def extract_paragraphs_with_positioning(pdf_path):
    """Extract paragraphs with their positioning information using improved logic"""
    doc = fitz.open(pdf_path)
    paragraphs = []
    
    for page_num, page in enumerate(doc):
        # Get text blocks with positioning
        blocks = page.get_text("dict")['blocks']
        page_paragraphs = []
        current_paragraph = ""
        current_y_start = None
        current_y_end = None
        
        for block in blocks:
            if block['type'] != 0:  # Skip non-text blocks
                continue
            
            for line in block['lines']:
                line_text = " ".join([span['text'] for span in line['spans']]).strip()
                if not line_text:
                    continue
                
                y_coord = min(span['bbox'][1] for span in line['spans'])
                
                # Check if this line starts a new paragraph
                if not current_paragraph or is_paragraph_break(current_paragraph, line_text):
                    # Save previous paragraph if it exists
                    if current_paragraph:
                        page_paragraphs.append({
                            'text': current_paragraph.strip(),
                            'y_start': current_y_start,
                            'y_end': current_y_end or current_y_start
                        })
                    
                    # Start new paragraph
                    current_paragraph = line_text
                    current_y_start = y_coord
                    current_y_end = y_coord
                else:
                    # Continue current paragraph
                    current_paragraph += " " + line_text
                    current_y_end = y_coord
        
        # Add the last paragraph
        if current_paragraph:
            page_paragraphs.append({
                'text': current_paragraph.strip(),
                'y_start': current_y_start,
                'y_end': current_y_end or current_y_start
            })
        
        # Add page number to each paragraph
        for para in page_paragraphs:
            para['page'] = page_num + 1
        
        paragraphs.extend(page_paragraphs)
    
    return paragraphs


def segment_sentences(text):
    """Segment text into sentences using simple regex"""
    return simple_sent_tokenize(text)


def create_simple_chunks(paragraphs, min_chunk_size=500, max_chunk_size=800):
    """Create simple chunks from paragraphs with sentence boundaries"""
    chunks = []
    current_chunk = ""
    current_page = None
    current_y_start = None
    current_paragraphs = []  # Track paragraphs in current chunk
    
    for para in paragraphs:
        para_text = para['text']
        para_size = len(para_text)
        
        # If adding this paragraph would exceed max size and we have content
        if current_chunk and len(current_chunk) + para_size > max_chunk_size:
            # Check if we can split at sentence boundary
            sentences = segment_sentences(current_chunk)
            if len(sentences) > 1:
                # Take all but the last sentence to stay within limits
                chunk_text = '. '.join(sentences[:-1]) + '.'
                if len(chunk_text) >= min_chunk_size:
                    # Use the y-coordinate of the first paragraph in the chunk
                    chunk_y_start = current_paragraphs[0]['y_start'] if current_paragraphs else current_y_start
                    chunks.append({
                        'text': chunk_text,
                        'page': current_page,
                        'y_start': chunk_y_start
                    })
                    # Start new chunk with the last sentence
                    current_chunk = sentences[-1]
                    current_paragraphs = [{'y_start': para['y_start']}]  # Reset with current paragraph
                else:
                    # Keep the whole chunk if it's too small
                    chunk_y_start = current_paragraphs[0]['y_start'] if current_paragraphs else current_y_start
                    chunks.append({
                        'text': current_chunk,
                        'page': current_page,
                        'y_start': chunk_y_start
                    })
                    current_chunk = para_text
                    current_paragraphs = [para]
            else:
                # No sentence boundary, just add the chunk
                chunk_y_start = current_paragraphs[0]['y_start'] if current_paragraphs else current_y_start
                chunks.append({
                    'text': current_chunk,
                    'page': current_page,
                    'y_start': chunk_y_start
                })
                current_chunk = para_text
                current_paragraphs = [para]
        else:
            # Add to current chunk
            if current_chunk:
                current_chunk += " " + para_text
                current_paragraphs.append(para)
            else:
                current_chunk = para_text
                current_page = para['page']
                current_y_start = para['y_start']
                current_paragraphs = [para]
    
    # Add the last chunk
    if current_chunk:
        chunk_y_start = current_paragraphs[0]['y_start'] if current_paragraphs else current_y_start
        chunks.append({
            'text': current_chunk,
            'page': current_page,
            'y_start': chunk_y_start
        })
    
    return chunks


def find_heading_for_chunk(chunk, headings_by_page):
    """Find the most appropriate heading for a chunk using improved positioning and content logic"""
    page_num = chunk['page']
    chunk_y = chunk['y_start']
    chunk_text = chunk['text'].lower()
    
    if page_num not in headings_by_page:
        return ""
    
    page_headings = headings_by_page[page_num]
    
    if not page_headings:
        return ""
    
    # If there's only one heading on the page, use it
    if len(page_headings) == 1:
        return page_headings[0]['text']
    
    # First, try to find a heading that appears in the chunk text (content-based)
    for heading in page_headings:
        heading_text = heading['text'].lower()
        # Check for exact match or partial match
        if heading_text in chunk_text or any(word in chunk_text for word in heading_text.split()):
            return heading['text']
    
    # If no heading appears in the text, try positioning-based approach
    headings_above = [h for h in page_headings if h['y_coord'] <= chunk_y]
    
    if headings_above:
        # Return the heading with the highest y-coordinate (closest to the chunk)
        closest_heading = max(headings_above, key=lambda x: x['y_coord'])
        return closest_heading['text']
    else:
        # If no heading is above the chunk, find the closest heading below
        headings_below = [h for h in page_headings if h['y_coord'] > chunk_y]
        if headings_below:
            # Return the heading with the lowest y-coordinate (closest below)
            closest_heading = min(headings_below, key=lambda x: x['y_coord'])
            return closest_heading['text']
        else:
            # If no headings below either, return the first heading on the page
            return page_headings[0]['text'] if page_headings else ""


def extract_chunks_with_headings(pdf_path, chunk_size=800):
    """
    Extract simple chunks with headings using paragraph-level chunking
    
    Args:
        pdf_path: Path to the PDF file
        chunk_size: Maximum chunk size in characters (default 800)
    """
    # Extract paragraphs with positioning
    paragraphs = extract_paragraphs_with_positioning(pdf_path)
    
    # Create simple chunks with sentence boundaries
    chunks = create_simple_chunks(paragraphs, min_chunk_size=500, max_chunk_size=chunk_size)
    
    # Get headings for context
    from heading_extractor import get_headings_by_page
    title, headings_by_page = get_headings_by_page(pdf_path)
    
    # Convert chunks to the expected format
    sections = []
    for chunk in chunks:
        heading = find_heading_for_chunk(chunk, headings_by_page)
        
        sections.append({
            'text': chunk['text'],
            'page': chunk['page'],
            'file': os.path.basename(pdf_path),
            'heading': heading
        })
    
    return sections


def extract_chunks_with_headings_advanced(pdf_path, chunk_size=800):
    """
    Simple advanced chunking - same as basic version for now
    """
    return extract_chunks_with_headings(pdf_path, chunk_size) 
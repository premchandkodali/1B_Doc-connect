import os
import fitz  # PyMuPDF
import json
from collections import Counter, defaultdict

# Heuristic: Use font size and font weight to classify headings
HEADING_LEVELS = ['Title', 'H1', 'H2', 'H3']


def clean_heading_text(text):
    """Clean heading text by truncating at colon and removing extra whitespace"""
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # If text contains a colon, take only the part before it
    if ':' in text:
        text = text.split(':')[0].strip()
    
    return text


def extract_lines_with_fonts(pdf_path):
    doc = fitz.open(pdf_path)
    lines = []
    for page_num, page in enumerate(doc, start=1):
        blocks = page.get_text("dict")['blocks']
        for block in blocks:
            if block['type'] != 0:
                continue
            for line in block['lines']:
                line_text = " ".join([span['text'] for span in line['spans']]).strip()
                if not line_text:
                    continue
                # Use the largest font size in the line (usually heading)
                max_font_size = max(span['size'] for span in line['spans'])
                # Use the most common font name in the line
                font_names = [span['font'] for span in line['spans']]
                font_name = Counter(font_names).most_common(1)[0][0]
                is_bold = any('Bold' in fn or 'bold' in fn for fn in font_names)
                # Get y-coordinate for positioning
                y_coord = min(span['bbox'][1] for span in line['spans'])
                lines.append({
                    'text': line_text,
                    'page': page_num - 1,  # page numbers start from 0
                    'font_size': max_font_size,
                    'font_name': font_name,
                    'is_bold': is_bold,
                    'y_coord': y_coord
                })
    return lines


def assign_heading_levels(lines):
    # Count font size frequencies
    font_size_counts = Counter(line['font_size'] for line in lines)
    total_lines = len(lines)
    
    # For PDFs with limited font sizes, use bold fonts as headings
    bold_lines = [line for line in lines if line['is_bold']]
    regular_lines = [line for line in lines if not line['is_bold']]
    
    # If we have bold text, use it as headings
    if bold_lines:
        outline = []
        for line in bold_lines:
            text = clean_heading_text(line['text'])
            # Skip very short lines or numbers
            if len(text) <= 3 or text.replace('.', '').isdigit():
                continue
            # Skip common form patterns
            skip_patterns = {'s.no', 'name', 'age', 'date', 'rs.', 'signature'}
            if text.lower() in skip_patterns:
                continue
            entry = {
                'level': 'H1',  # Treat bold text as H1
                'text': text,
                'page': line['page'],
                'y_coord': line['y_coord']
            }
            outline.append(entry)
        return None, outline
    
    # Fallback: use font size differences
    # Most common font size is body text
    if font_size_counts:
        body_font_size, _ = font_size_counts.most_common(1)[0]
        # Only consider font sizes that are rare (<20% of lines)
        rare_font_sizes = [size for size, count in font_size_counts.items() if count / total_lines < 0.2]
        # Sort rare font sizes descending (largest = Title, then H1, ...)
        rare_font_sizes = sorted(rare_font_sizes, reverse=True)
        # Map rare font sizes to heading levels
        size_to_level = {}
        for i, size in enumerate(rare_font_sizes[:len(HEADING_LEVELS)]):
            size_to_level[size] = HEADING_LEVELS[i]
        # Assign level to each line
        outline = []
        title_lines = []
        for line in lines:
            # Ignore body text font size
            if line['font_size'] == body_font_size:
                continue
            level = size_to_level.get(line['font_size'])
            if not level:
                continue  # Not a heading
            # Ignore lines that are just numbers or very short (<=3 chars, e.g., '1.', '2.')
            text = clean_heading_text(line['text'])
            if len(text) <= 3 or text.replace('.', '').isdigit():
                continue
            # Optionally: ignore lines that match common form/table patterns (e.g., 'S.No', 'Name', 'Age', 'Date')
            skip_patterns = {'s.no', 'name', 'age', 'date', 'rs.', 'signature'}
            if text.lower() in skip_patterns:
                continue
            if level == 'Title':
                title_lines.append(text)
            else:
                entry = {
                    'level': level,
                    'text': text,
                    'page': line['page'],
                    'y_coord': line['y_coord']
                }
                outline.append(entry)
        title = ' '.join(title_lines) if title_lines else None
        return title, outline
    
    return None, []


def get_headings_by_page(pdf_path):
    """Extract headings organized by page number"""
    lines = extract_lines_with_fonts(pdf_path)
    title, outline = assign_heading_levels(lines)
    
    # Group headings by page
    headings_by_page = defaultdict(list)
    for entry in outline:
        headings_by_page[entry['page']].append({
            'text': entry['text'],
            'level': entry['level'],
            'y_coord': entry['y_coord']
        })
    
    return title, headings_by_page


def find_heading_for_chunk(chunk_page, chunk_text, headings_by_page):
    """Find the most appropriate heading for a chunk based on page and content"""
    if chunk_page not in headings_by_page:
        return ""
    
    # Get headings from the same page
    page_headings = headings_by_page[chunk_page]
    
    if not page_headings:
        return ""
    
    # If there's only one heading on the page, use it
    if len(page_headings) == 1:
        return page_headings[0]['text']
    
    # Try to find the most relevant heading by checking if any heading text appears in the chunk
    for heading in page_headings:
        heading_words = set(heading['text'].lower().split())
        chunk_words = set(chunk_text.lower().split())
        # Check for word overlap
        if len(heading_words.intersection(chunk_words)) > 0:
            return heading['text']
    
    # If no direct match, return the first heading (usually the main section heading)
    return page_headings[0]['text']


def extract_chunks_with_headings(pdf_path, chunk_size=500):  # Increased from 200 to 500
    """Extract chunks with their corresponding headings"""
    doc = fitz.open(pdf_path)
    title, headings_by_page = get_headings_by_page(pdf_path)
    
    sections = []
    for page_num in range(len(doc)):
        page = doc[page_num]
        text = page.get_text()
        
        # Simple chunking: split by paragraphs, then merge to chunk_size
        paras = [p.strip() for p in text.split('\n') if p.strip()]
        chunk = ''
        for para in paras:
            if len(chunk) + len(para) < chunk_size:
                chunk += (' ' if chunk else '') + para
            else:
                if chunk:
                    # Find heading for this chunk
                    heading = find_heading_for_chunk(page_num, chunk, headings_by_page)
                    sections.append({
                        'text': chunk,
                        'page': page_num + 1,
                        'file': os.path.basename(pdf_path),
                        'heading': heading
                    })
                chunk = para
        if chunk:
            # Find heading for this chunk
            heading = find_heading_for_chunk(page_num, chunk, headings_by_page)
            sections.append({
                'text': chunk,
                'page': page_num + 1,
                'file': os.path.basename(pdf_path),
                'heading': heading
            })
    
    return sections 
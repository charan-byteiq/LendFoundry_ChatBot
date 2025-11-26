import pdfplumber
import re
import json

def load_chunks(pdf_path: str) -> list:
    with pdfplumber.open(pdf_path) as pdf:
        full_text = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

    pattern = re.compile(
        r"--- START SEGMENT ---\s*TAGS:\s*\[(.*?)\]\s*CONTENT:\s*((?:.|\n)*?)--- END SEGMENT ---",
        re.MULTILINE
    )

    matches = pattern.findall(full_text)
    print(f"✅ Found {len(matches)} segments in the PDF.")

    chunks = []
    for tags_text, content_text in matches:
        tags = [tag.strip() for tag in tags_text.split(",")]
        content = content_text.strip()
        chunks.append({"tags": tags, "content": content})
    return chunks


def save_chunks_to_json(chunks, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=2, ensure_ascii=False)
    print(f"✅ Saved {len(chunks)} chunks to {path}")

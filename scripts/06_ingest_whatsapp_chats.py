import os
import sys
import json
import time
import re
import argparse
from pathlib import Path
from datetime import datetime

from google import genai
from google.genai import types as genai_types
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import PointStruct
from dotenv import load_dotenv
from utils import sanitize_text

load_dotenv()

QDRANT_URL      = os.getenv("QDRANT_URL")
QDRANT_API_KEY  = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = os.getenv("QDRANT_COLLECTION_PHASE1", "WFPB recipes")
GOOGLE_API_KEY  = os.getenv("GOOGLE_API_KEY")
FASTEMBED_MODEL = os.getenv("FASTEMBED_MODEL", "BAAI/bge-large-en-v1.5")

PROJECT_ROOT   = Path(__file__).parent.parent
CHAT_FILE       = PROJECT_ROOT / "data" / "raw" / "text" / "WFPB Chats.txt"
DATA_PROCESSED  = PROJECT_ROOT / "data" / "processed" / "chats"

EXTRACTION_PROMPT = """
You are a top-tier WFPB recipe extractor. I will provide a chunk of a WhatsApp chat about Whole Food Plant-Based cooking.
Your task is to identify and extract any useful recipes, cooking techniques, tips, or informative discussions from the log.
You must synthesize scattered messages into a single coherent entry if they pertain to the same recipe or topic.

Return ONLY a valid JSON array of objects. Do not wrap in markdown or add explanations.
Each object should have the exact following structure:
{
  "recipe_name": "Title of the recipe or discussion topic (e.g., 'Air-fried Aloo Bonda', 'Tips for roasting Makhana')",
  "creator": "Name of the person sharing it (if clear, else 'Group Member')",
  "category": "Choose one: 'Recipe', 'Tip', or 'Discussion'",
  "text": "Detailed contents including ingredients, method, or key points discussed. Write this coherently."
}

If there are no recipes, tips, or meaningful discussions in the chunk, return an empty JSON array: []

Note: If the creator's identity is just a phone number (e.g. +1 123...), replace it with 'WFPB member'.
"""

def extract_from_chunk(chunk_text: str, gemini, chunk_index: int) -> list:
    print(f"  [Extract] Sending chunk {chunk_index} to Gemini...")
    try:
        response = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=[EXTRACTION_PROMPT, chunk_text],
            config=genai_types.GenerateContentConfig(temperature=0),
        )
        raw_text = response.text.strip()
        if raw_text.startswith("```"):
            lines = raw_text.split("\n")
            raw_text = "\n".join(lines[1:-1])
        data = json.loads(raw_text)
        if not isinstance(data, list):
            data = [data]
        return data
    except Exception as e:
        print(f"  [ERROR] Gemini extraction failed for chunk {chunk_index}: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Ingest WhatsApp chatting to Qdrant")
    parser.add_argument("--extract-only", action="store_true")
    args = parser.parse_args()

    if not CHAT_FILE.exists():
        print(f"[ERROR] Chat file not found: {CHAT_FILE}")
        sys.exit(1)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    
    # 1. Read and chunk file
    with open(CHAT_FILE, "r", encoding="utf-8") as f:
        lines = f.readlines()
        
    chunk_size = 1000
    overlap = 50
    chunks = []
    
    for i in range(0, len(lines), chunk_size - overlap):
        chunk_lines = lines[i : i + chunk_size]
        chunks.append("".join(chunk_lines))
        if i + chunk_size >= len(lines):
            break

    print(f"\n[INFO] Split chat into {len(chunks)} chunks.")

    gemini = genai.Client(api_key=GOOGLE_API_KEY)
    
    # 2. Extract JSON from chunks
    all_extracted = []
    for i, chunk_text in enumerate(chunks):
        out_file = DATA_PROCESSED / f"chunk_{i:03d}.json"
        if out_file.exists():
            print(f"  [Load] Chunk {i} loaded from JSON")
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        else:
            data = extract_from_chunk(chunk_text, gemini, i)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            time.sleep(1.5)  # Rate limiting
        
        for item in data:
            item["chunk_index"] = i
            item["source_pdf"] = "WFPB Chats.txt"
        
        all_extracted.extend(data)

    # 3. Sanitize data (Remove phone numbers and update files)
    print("\n[INFO] Sanitizing creator names (Privacy Check)...")
    for i in range(len(chunks)):
        out_file = DATA_PROCESSED / f"chunk_{i:03d}.json"
        if out_file.exists():
            with open(out_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            modified = False
            for item in data:
                # Sanitize BOTH creator and text fields
                for field in ["creator", "text", "recipe_name"]:
                    if field in item:
                        old_val = item[field]
                        new_val = sanitize_text(old_val)
                        if old_val != new_val:
                            item[field] = new_val
                            modified = True
            
            if modified:
                with open(out_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                print(f"  [Update] Chunk {i} sanitized and saved.")

    # Re-build all_extracted for embedding
    all_extracted = []
    for i in range(len(chunks)):
        out_file = DATA_PROCESSED / f"chunk_{i:03d}.json"
        with open(out_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                item["chunk_index"] = i
                item["source_pdf"] = "WFPB Chats.txt"
            all_extracted.extend(data)

    # 4. Embed text
    print("\n[INFO] Initializing FastEmbed model...")
    embedder = TextEmbedding(model_name=FASTEMBED_MODEL)
    print("\n[INFO] Connected to Qdrant...")
    qdrant = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    
    points = []
    for i, item in enumerate(all_extracted):
        text = f"Title: {item.get('recipe_name', 'Unknown')}\n"
        text += f"Creator: {item.get('creator', 'Unknown')}\n"
        text += f"Category: {item.get('category', 'Chat Log')}\n"
        text += f"Content: {item.get('text', '')}"
        
        item["text"] = text
        embedding = list(embedder.embed([text]))[0].tolist()
        
        # Consistent ID hashing
        str_id = f"chat_item_{item['chunk_index']}_{i}"
        point_id = abs(hash(str_id)) % (2**63)
        item["id"] = str_id
        
        points.append(PointStruct(
            id=point_id,
            vector=embedding,
            payload=item
        ))

    # 4. Upsert to Qdrant
    if points:
        batch_size = 32
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            qdrant.upsert(
                collection_name=COLLECTION_NAME,
                points=batch,
                wait=True
            )
            total_upserted += len(batch)
            print(f"  [Upsert] {total_upserted}/{len(points)} points upserted")
    
    print("\n[DONE] WhatsApp chat ingestion complete!")

if __name__ == "__main__":
    main()

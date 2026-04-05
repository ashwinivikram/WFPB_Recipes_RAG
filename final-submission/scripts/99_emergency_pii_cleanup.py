import os
import json
from pathlib import Path
from utils import sanitize_text

DATA_PROCESSED = Path(__file__).parent.parent / "data" / "processed"

def sanitize_recursive(data):
    if isinstance(data, dict):
        return {k: sanitize_recursive(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [sanitize_recursive(item) for item in data]
    elif isinstance(data, str):
        return sanitize_text(data)
    else:
        return data

def main():
    if not DATA_PROCESSED.exists():
        print(f"[ERROR] Processed data directory not found: {DATA_PROCESSED}")
        return

    print(f"\n[START] Scrubbing PII from all JSON files in {DATA_PROCESSED}...")
    
    count = 0
    modified_count = 0
    
    for root, dirs, files in os.walk(DATA_PROCESSED):
        for file in files:
            if file.endswith(".json"):
                file_path = Path(root) / file
                with open(file_path, "r", encoding="utf-8") as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        print(f"  [ERROR] Failed to load {file_path}")
                        continue
                
                # Sanitize the entire structure
                new_data = sanitize_recursive(data)
                
                # Check if it was modified (by comparing string representations or just saving anyway)
                # To be safe and thorough, we save everything back
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump(new_data, f, indent=2)
                
                count += 1
                if count % 50 == 0:
                    print(f"  [Progress] Processed {count} files...")

    print(f"\n[DONE] PII scrub complete. {count} files were sanitized.")

if __name__ == "__main__":
    main()

"""
06_chunk_with_strategy.py
-------------------------
Week 2 chunking strategy: document-level with sub-recipe boundary detection.

Reads all processed recipe JSONs from data/processed/ and applies the Week 2
chunking strategy:

  1. SKIP   — empty chunks (recipe_name == "") — cover/TOC pages
  2. SPLIT  — recipe cards that embed a sub-recipe within the instructions.
              Detected by ALL-CAPS named-food section headers (e.g. "WALNUT
              MUSHROOM PATE:", "TZATZIKI SAUCE:", "KATHI ROLLS:").
              Each card becomes 2 chunks: sub-recipe component + main assembly.
  3. PASS   — all other recipe cards unchanged (one card = one chunk)

Split naming logic:
  - Component chunk (earlier text):  recipe_name = first food section header
    found in that portion (e.g. "Walnut Mushroom Pate", "Sweet Potato Paratha")
  - Assembly chunk  (later text):    recipe_name = original recipe name
    (or title-cased split header when it differs from original)
  Both chunks keep original creator, category, and source_pdf in payload.

Output:
  Writes data/processed/week2_chunks.json — a JSON list of all chunks.
  Split chunks have needs_embedding=True; script 07 regenerates their vectors.
  Unchanged chunks will have embeddings regenerated in script 07 for consistency.

Usage:
    python scripts/06_chunk_with_strategy.py
    python scripts/06_chunk_with_strategy.py --dry-run   # Report only, no output

Author: Ashwini Vikram
Project: WFPB Recipe RAG System — Week 2
Data Source: Thankful2Plants.com (CC BY-NC-ND 4.0)
"""

import json
import re
import sys
import argparse
from pathlib import Path
from copy import deepcopy

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJECT_ROOT   = Path(__file__).parent.parent
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
OUTPUT_FILE    = DATA_PROCESSED / "week2_chunks.json"

# ── Sub-recipe detection ───────────────────────────────────────────────────────
# Words that indicate a PROCESS STEP rather than a named sub-recipe.
# A header made up entirely of these words will NOT be treated as a split point.
PROCESS_WORDS = frozenset({
    "BATTER", "DOUGH", "STUFFING", "FILLING", "COOK", "COOKING",
    "STEAMING", "STEAM", "BAKE", "BAKING", "TIPS", "TIP",
    "ROLL", "ROLLING", "STORE", "STORAGE", "SERVING", "METHOD",
    "STEPS", "STEP", "PREP", "PREPARATION", "ASSEMBLY", "GARNISH",
    "TOPPING", "MARINADE", "MARINATE", "DIRECTIONS", "PROCEDURE",
    "GRIND", "FERMENT", "SOAK", "SHAPE", "KNEAD",
    # Serving / annotation headers
    "SERVE", "SOAKING", "NOTE", "NOTES",
    # Indian cooking technique headers (finishing steps, not standalone recipes)
    "TADKA", "TEMPERING",
    # Generic spice/seasoning/prep headers
    "SPICE", "RUB", "MIX", "MASALA", "PASTE", "DRY",
    # Equipment/baking context headers
    "PAN",
    # WFPB ingredient-category labels used as section headers
    "RAINBOW", "VEGGIES",
})

# Regex: ALL-CAPS section headers (≥4 chars) followed by a colon.
# Does NOT require a newline after the colon — handles both:
#   "HEADER NAME:\nInstruction text"   and
#   "HEADER NAME: Instruction text"
HEADER_RE = re.compile(r"(?<![A-Za-z])([A-Z][A-Z ]{2,39}[A-Z]):\s*", re.MULTILINE)


def _is_process_header(header: str) -> bool:
    """Return True if every word in the header is a known process word."""
    return set(header.upper().split()).issubset(PROCESS_WORDS)


def _get_first_food_header(text: str) -> str | None:
    """
    Find the first ALL-CAPS food-named section header in a text string.
    Returns the title-cased header name, or None if none found.
    """
    for m in HEADER_RE.finditer(text):
        name = m.group(1).strip()
        if not _is_process_header(name):
            return name.title()
    return None


def find_split_position(instructions: str, original_name: str) -> tuple[int, str] | None:
    """
    Find the best character position to split an instructions string.

    Strategy:
        1. Find all ALL-CAPS section headers.
        2. Keep only food-named headers (discard pure process words).
        3. Identify the LAST food-named header — this is the main dish assembly.
        4. Everything before it = sub-recipe components; everything from it = main.

    Safety checks:
        - Skip if the split-at header matches the original recipe name AND
          there is no distinct food header in the earlier portion — this means
          the recipe only has process sections (BATTER, GRIND, etc.) before the
          main dish section, and splitting adds no retrieval value.
        - Skip if there is not enough content before the split point.

    Returns:
        (position_in_instructions, header_name) or None if no valid split.
    """
    matches = [
        (m.start(), m.group(1).strip())
        for m in HEADER_RE.finditer(instructions)
    ]

    # Separate food-named from process headers
    food_headers = [(pos, name) for pos, name in matches if not _is_process_header(name)]

    if not food_headers:
        return None

    last_pos, last_name = food_headers[-1]

    # Safety: need enough content before the split to form a useful chunk
    content_before = instructions[:last_pos].strip()
    if len(content_before.split()) < 8:
        return None

    # Safety: if there is no distinct food header before the split AND the
    # split-at header is essentially the recipe name itself, this is just a
    # multi-step single recipe (e.g. BATTER/GRIND/FERMENT/ADAI) — skip.
    earlier_food_name = _get_first_food_header(content_before)
    if earlier_food_name is None:
        split_title = last_name.title().lower()
        original_lower = original_name.lower()
        if split_title in original_lower or original_lower in split_title:
            return None

    return last_pos, last_name


def _build_text(recipe: dict) -> str:
    """
    Reconstruct the embedding text string from a recipe dict.
    Mirrors build_embedding_text() in create_pipeline_02.py.
    """
    parts = []
    if recipe.get("recipe_name"):
        parts.append(f"Recipe: {recipe['recipe_name']}")
    if recipe.get("creator"):
        parts.append(f"Creator: {recipe['creator']}")
    if recipe.get("category"):
        parts.append(f"Category: {recipe['category']}")
    if recipe.get("all_ingredients_flat"):
        parts.append(f"Ingredients: {recipe['all_ingredients_flat']}")
    if recipe.get("cooking_methods"):
        methods = (
            ", ".join(recipe["cooking_methods"])
            if isinstance(recipe["cooking_methods"], list)
            else recipe["cooking_methods"]
        )
        parts.append(f"Cooking methods: {methods}")
    if recipe.get("instructions"):
        parts.append(f"Instructions: {recipe['instructions']}")
    if recipe.get("notes"):
        parts.append(f"Notes: {recipe['notes']}")
    return "\n".join(parts)


def split_recipe(recipe: dict) -> list[dict]:
    """
    Apply the Week 2 chunking strategy to a single recipe dict.

    Returns:
        []         — if the recipe is empty (cover/TOC page)
        [recipe]   — if no sub-recipe boundary detected (pass through)
        [comp, asm]— if split: component chunk + assembly chunk
    """
    # ── Rule 1: skip empty cover/TOC pages ────────────────────────────────────
    if not recipe.get("recipe_name"):
        return []

    instructions   = recipe.get("instructions") or ""
    original_name  = recipe["recipe_name"]
    split          = find_split_position(instructions, original_name)

    # ── Rule 2: no sub-recipe detected ────────────────────────────────────────
    if split is None:
        return [recipe]

    split_pos, split_header = split
    earlier_instructions = instructions[:split_pos].strip()
    later_instructions   = instructions[split_pos:].strip()

    # ── Naming logic ──────────────────────────────────────────────────────────
    # Component chunk: use the first food section header found in the earlier
    # portion as the recipe_name (e.g. "Walnut Mushroom Pate", "Zucchini Chutney").
    # Falls back to original name if none found.
    comp_name = _get_first_food_header(earlier_instructions) or original_name

    # Safety: if comp_name fell back to the original name it means no distinct
    # sub-recipe header was found in the earlier portion — the split point is
    # just a process section at the end (e.g. SERVE:, NOTE:, KALE CHIPS:).
    # Splitting adds no retrieval value, so pass through unchanged.
    if comp_name == original_name:
        return [recipe]

    # Assembly chunk: keep the original recipe name so it is still findable by
    # its full name.
    asm_name = original_name

    # ── Build component chunk (sub-recipe / prep steps) ───────────────────────
    comp = deepcopy(recipe)
    comp["id"]                  = recipe["id"] + "_component"
    comp["recipe_name"]         = comp_name
    comp["instructions"]        = earlier_instructions
    comp["text"]                = _build_text(comp)
    comp["embedding"]           = None          # Regenerated in script 07
    comp["chunk_type"]          = "component"
    comp["parent_recipe_name"]  = original_name
    comp["split_from"]          = recipe["id"]

    # ── Build assembly chunk (main dish) ──────────────────────────────────────
    asm = deepcopy(recipe)
    asm["id"]                   = recipe["id"] + "_assembly"
    asm["recipe_name"]          = asm_name
    asm["instructions"]         = later_instructions
    asm["text"]                 = _build_text(asm)
    asm["embedding"]            = None           # Regenerated in script 07
    asm["chunk_type"]           = "assembly"
    asm["parent_recipe_name"]   = original_name
    asm["split_from"]           = recipe["id"]

    return [comp, asm]


def load_all_recipes() -> list[dict]:
    """
    Load every recipe JSON from data/processed/.
    PDF categories → one dict per file.
    Chat files → stored as JSON arrays, each item is one dict.
    """
    recipes = []
    for cat_dir in sorted(DATA_PROCESSED.iterdir()):
        if not cat_dir.is_dir():
            continue
        for jf in sorted(cat_dir.glob("*.json")):
            if jf.name == "week2_chunks.json":
                continue
            try:
                with open(jf, encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    recipes.extend(data)
                else:
                    recipes.append(data)
            except Exception as e:
                print(f"  [WARN] Could not load {jf}: {e}")
    return recipes


def apply_strategy(recipes: list[dict]) -> tuple[list[dict], dict]:
    """Apply Week 2 chunking strategy. Returns (chunks, stats)."""
    chunks = []
    stats  = {
        "input_total":    len(recipes),
        "skipped_empty":  0,
        "passed_through": 0,
        "split_cards":    0,
        "output_total":   0,
    }

    for recipe in recipes:
        result = split_recipe(recipe)

        if len(result) == 0:
            stats["skipped_empty"] += 1
        elif len(result) == 1:
            stats["passed_through"] += 1
            chunks.extend(result)
        else:
            stats["split_cards"] += 1
            chunks.extend(result)
            print(
                f"  [SPLIT] '{recipe.get('recipe_name','')}' "
                f"→ component: '{result[0]['recipe_name']}' "
                f"+ assembly: '{result[1]['recipe_name']}'"
            )

    stats["output_total"] = len(chunks)
    return chunks, stats


def print_summary(stats: dict):
    print("\n══ Week 2 Chunking Summary ═══════════════════════════")
    print(f"  Input chunks (Week 1 naive) : {stats['input_total']}")
    print(f"  Skipped (empty/cover pages) : {stats['skipped_empty']}")
    print(f"  Passed through unchanged    : {stats['passed_through']}")
    print(f"  Recipe cards split          : {stats['split_cards']}")
    print(f"  Net new chunks from splits  : +{stats['split_cards']}")
    print(f"  Output chunks (Week 2)      : {stats['output_total']}")
    print("══════════════════════════════════════════════════════")


def main():
    parser = argparse.ArgumentParser(description="Apply Week 2 chunking strategy")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report splits without writing output file",
    )
    args = parser.parse_args()

    print("\n=== 06_chunk_with_strategy.py — Week 2 Chunking ===\n")
    print(f"  Strategy : Document-level + sub-recipe boundary detection")
    print(f"  Input    : {DATA_PROCESSED}\n")

    print("── Loading processed recipes ──")
    recipes = load_all_recipes()
    print(f"  Loaded {len(recipes)} recipe records\n")

    print("── Applying Week 2 strategy ──")
    chunks, stats = apply_strategy(recipes)

    print_summary(stats)

    if args.dry_run:
        print("\n[DRY RUN] No output file written.")
        return

    # Write output (without raw embedding arrays — script 07 regenerates them)
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    output = []
    for chunk in chunks:
        c = {k: v for k, v in chunk.items() if k != "embedding"}
        c["needs_embedding"] = True   # Script 07 always regenerates for consistency
        output.append(c)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[OK] Week 2 chunks written to: {OUTPUT_FILE}")
    print(f"     {stats['output_total']} total chunks")
    print(f"\n     Next step: python scripts/07_index_with_strategy.py\n")


if __name__ == "__main__":
    main()

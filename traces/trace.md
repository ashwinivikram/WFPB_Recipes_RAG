# Week 1 RAG Traces

**Project:** WFPB Recipe RAG System — Thankful2Plants.com  
**Author:** Ashwini Vikram  
**Collection:** mcp_phase1_baseline  
**Embedding model:** BAAI/bge-large-en-v1.5 (dim=1024)  
**LLM:** Gemini 2.5 Flash  
**Date:** 2026-02-21  
**Total queries:** 10  

---

## Query 1: What recipes can I make with avocado and tomato?

**Question:** What recipes can I make with avocado and tomato?

**Retrieved Chunks:**
1. `Sandwich Head` by Frank Lee (score: 0.6730) — Sandwiches & Pita Pockets — Whole Food Plant-Based.pdf
2. `Lentil Quinoa Uttapam | Tomato Chutney` by Sharmila Vedam (score: 0.6448) — Savory Pancakes & Waffles
3. `Jicama Chips with Guacamole` by Frank Lee (score: 0.6435) — Savory Snacks
4. `Tomato Slice Chaat` by Ashwini Vikram (score: 0.6418) — Savory Snacks
5. `Mogri Nasturtium Paan` by Ravi Belwal (score: 0.6300) — Savory Snacks

**Generated Answer:**
Based on the Thankful2Plants.com recipe collection, here are the recipes that use both avocado and tomato:

- **Sandwich Head** by Frank Lee — includes avocado and tomato among its ingredients for a lentil avocado spread and toppings on whole grain bread.
- **Jicama Chips with Guacamole** by Frank Lee — features guacamole made from avocado, red onion, tomato, cilantro, and lemon juice, served with seasoned jicama chips.

**Assessment:**
- Retrieval quality: Good — top results contain recipes with both avocado and tomato; 2 of 5 retrieved chunks are directly relevant
- Answer quality: Good — LLM correctly identified only the directly relevant recipes without hallucinating other ingredients
- Was the right context retrieved? Yes
- Notes: Remaining 3 chunks (Uttapam, Tomato Chaat, Paan) have tomato but not avocado — the LLM correctly filtered them out of the answer

---

## Query 2: Show me recipes that use edamame

**Question:** Show me recipes that use edamame

**Retrieved Chunks:**
1. `Edamame & Hazelnuts` by Gurmeet Manku (score: 0.7236) — Savory Snacks
2. `Karadaiyan Nombu Adai (Savory)` by Kanthi Suresh (score: 0.6928) — Savory Pancakes & Waffles
3. `Stuffed Paratha Pockets` by Dr Sirisha Potluri (score: 0.6917) — Sandwiches & Pita Pockets
4. `Chickpea Omelette with Bean Shoots & Mushrooms` by Frank Lee (score: 0.6804) — Savory Pancakes & Waffles
5. `Tofu & Sweet Potato Sandwich` by Gurmeet Manku (score: 0.6736) — Sandwiches & Pita Pockets

**Generated Answer:**
Here is a recipe from Thankful2Plants.com that uses edamame:

- **Edamame & Hazelnuts** by Gurmeet Manku — Ingredients: edamame, hazelnuts. Cooking methods: no-cook. Source: Savory Snacks — Whole Food Plant-Based.pdf, page 2

**Assessment:**
- Retrieval quality: Good — the one true edamame recipe (Edamame & Hazelnuts) ranked #1 with a strong score of 0.7236; other results are false positives
- Answer quality: Good — LLM correctly returned only the recipe that actually contains edamame and did not hallucinate others
- Was the right context retrieved? Yes — top result is correct
- Notes: Surprising that only 1 recipe across 4 PDFs uses edamame; false positives in ranks 2-5 indicate that the embedding space for legume-related ingredients is somewhat clustered

---

## Query 3: What recipes did Sirisha Potluri create?

**Question:** What recipes did Sirisha Potluri create?

**Retrieved Chunks:**
1. `Chickpea Chaat Salad` by Dr Sirisha Potluri (score: 0.6465) — Savory Snacks
2. `Lauki Leaves Patra` by Manisha Deora (score: 0.6429) — Tikkis, Cutlets, Falafel, Dumplings
3. `Stuffed Paratha Pockets` by Dr Sirisha Potluri (score: 0.6336) — Sandwiches & Pita Pockets
4. `Ezekiel Kathi Roll` by Kumar Natarajan (score: 0.6308) — Sandwiches & Pita Pockets
5. `Karadaiyan Nombu Adai (Savory)` by Kanthi Suresh (score: 0.6273) — Savory Pancakes & Waffles

**Generated Answer:**
Thankful2Plants.com features the following recipes created by Dr Sirisha Potluri:

- **Chickpea Chaat Salad** — Source: Savory Snacks — Whole Food Plant-Based.pdf, page 22
- **Stuffed Paratha Pockets** — Source: Sandwiches & Pita Pockets — Whole Food Plant-Based.pdf, page 44

**Assessment:**
- Retrieval quality: Partial — only 2 of Dr Sirisha Potluri's recipes appear in top-5; she has at least 4 recipes across the indexed PDFs (also: Veggie Loaded Uthappam, Pita Pockets with Tzatziki Sauce, Chickpea Tofu Omelette)
- Answer quality: Partial — the answer is accurate for what was retrieved, but incomplete; user would not know other recipes exist
- Was the right context retrieved? Partially — top-5 only captures a subset of creator's recipes
- If not, what was missing? Pure vector similarity with a shorthand name ("Sirisha Potluri" vs "Dr Sirisha Potluri") did not recall all recipes; metadata filtering on creator field would solve this

---

## Query 4: Show me recipes by Dr Sirisha Potluri

**Question:** Show me recipes by Dr Sirisha Potluri

**Retrieved Chunks:**
1. `Stuffed Paratha Pockets` by Dr Sirisha Potluri (score: 0.6693) — Sandwiches & Pita Pockets
2. `Veggie Loaded Uthappam` by Dr Sirisha Potluri (score: 0.6475) — Savory Pancakes & Waffles
3. `Chickpea Chaat Salad` by Dr Sirisha Potluri (score: 0.6454) — Savory Snacks
4. `Lauki Leaves Patra` by Manisha Deora (score: 0.6426) — Tikkis, Cutlets, Falafel, Dumplings
5. `Brown Rice Farra` by Sharmila Vedam (score: 0.6404) — Tikkis, Cutlets, Falafel, Dumplings

**Generated Answer:**
Here are the recipes by Dr Sirisha Potluri from the Thankful2Plants collection:

- **Stuffed Paratha Pockets** — Source: Sandwiches & Pita Pockets — Whole Food Plant-Based.pdf, page 44
- **Veggie Loaded Uthappam** — Source: Savory Pancakes & Waffles — Whole Food Plant-Based.pdf, page 23
- **Chickpea Chaat Salad** — Source: Savory Snacks — Whole Food Plant-Based.pdf, page 22

**Assessment:**
- Retrieval quality: Good — using "Dr Sirisha Potluri" exact prefix returned 3 of her recipes in top-3 (contrast with Query 3 where "Sirisha Potluri" shorthand only returned 2)
- Answer quality: Good — LLM correctly reported all 3 retrieved recipes and attributed them correctly
- Was the right context retrieved? Yes — but still only a subset; this confirms that exact name phrasing matters for creator queries
- Notes: Rank 1 vs Query 3 shows full title "Dr Sirisha Potluri" gives better recall; metadata filters would be necessary for exhaustive creator queries

---

## Query 5: How do I make Walnut Mushroom Pate?

**Question:** How do I make Walnut Mushroom Pate?

**Retrieved Chunks:**
1. `Ezekiel Sandwich with Walnut Mushroom Pate` by Kumar Natarajan (score: 0.8061) — Sandwiches & Pita Pockets
2. `Chinese Gnocchi in Mushroom Sauce` by Frank Lee (score: 0.7027) — Tikkis, Cutlets, Falafel, Dumplings
3. `Stuffed Paratha Pockets` by Dr Sirisha Potluri (score: 0.6758) — Sandwiches & Pita Pockets
4. `Purple Cabbage Patties` by Kiran Sharma (score: 0.6739) — Tikkis, Cutlets, Falafel, Dumplings
5. `Falafel` by Leena Menon (score: 0.6634) — Tikkis, Cutlets, Falafel, Dumplings

**Generated Answer:**
**Walnut Mushroom Pate** by Kumar Natarajan (Source: Sandwiches & Pita Pockets, page 4):

1. Dry roast the walnuts. Set aside to cool.
2. Sauté mushrooms, onion & garlic for a few minutes (without oil). Let them cool down.
3. Blend the dry roasted walnuts and sautéed onion, garlic & mushroom, along with parsley, green chili and black pepper.

*This information is attributed to Thankful2Plants.com.*

**Assessment:**
- Retrieval quality: Good — the exact recipe ranked #1 with a very high score of 0.8061; specific recipe name queries work extremely well
- Answer quality: Good — step-by-step instructions are accurately reproduced from the source
- Was the right context retrieved? Yes
- Notes: Score of 0.8061 vs ~0.65 for ranked 2-5 shows a clear relevance gap; specific named-recipe queries are the strongest retrieval use case for this corpus

---

## Query 6: What is the cooking strategy for Tofu Banh Mi?

**Question:** What is the cooking strategy for Tofu Banh Mi?

**Retrieved Chunks:**
1. `Tofu Banh Mi` by Leena Menon (score: 0.8323) — Sandwiches & Pita Pockets
2. `Tofu Bhurji on Ezekiel` by Kumar Natarajan (score: 0.7008) — Sandwiches & Pita Pockets
3. `Yum Cha` by Frank Lee (score: 0.6991) — Tikkis, Cutlets, Falafel, Dumplings
4. `Chickpea Tofu Omelette` by Dr Sirisha Potluri (score: 0.6951) — Savory Pancakes & Waffles
5. `Fruity Tofu` by Gurmeet Manku (score: 0.6902) — Savory Snacks

**Generated Answer:**
The cooking strategy for Leena Menon's Tofu Banh Mi involves a combination of baking, toasting, and no-cook steps:

- **Tofu Preparation:** Firm tofu is pressed, sliced, marinated overnight in low sodium soy sauce, then baked at 350°F for 20-30 minutes.
- **Pickled Vegetables:** Carrot, radish, and cucumber marinated in rice vinegar with date sugar. No-cook.
- **Assembly:** Ezekiel bread toasted, spread with Cashew Cheese + Sriracha, topped with baked tofu and pickled vegetables. Optional jalapeños.

Source: Sandwiches & Pita Pockets — Whole Food Plant-Based.pdf, page 11

**Assessment:**
- Retrieval quality: Good — correct recipe ranked #1 with the highest score seen in any query (0.8323); strategy queries with specific recipe names work perfectly
- Answer quality: Good — structured breakdown of cooking methods is accurate and clear
- Was the right context retrieved? Yes
- Notes: Ranks 2-5 are all tofu recipes (makes sense semantically); score gap between rank 1 (0.83) and rank 2 (0.70) confirming the named recipe was found with high confidence

---

## Query 7: Suggest quick weekday lunch ideas that need no cooking

**Question:** Suggest quick weekday lunch ideas that need no cooking

**Retrieved Chunks:**
1. `Grilled Pizza Sandwich` by Padma Subramanian (score: 0.6231) — Sandwiches & Pita Pockets
2. `Airport Sandwich` by Gurmeet Manku (score: 0.6163) — Sandwiches & Pita Pockets
3. `Chutney Sandwich with Lentil Wrap` by Kusum Dhairyawan (score: 0.6102) — Sandwiches & Pita Pockets
4. `Ragda` by Kiran Sharma (score: 0.6095) — Tikkis, Cutlets, Falafel, Dumplings
5. `Khandvi` by Sharmila Vedam (score: 0.6062) — Savory Snacks

**Generated Answer:**
Based on the Thankful2Plants collection, only one recipe meets the criteria of being a quick weekday lunch that needs no cooking:

- **Airport Sandwich** by Gurmeet Manku — Made with Ezekiel 4:9 Low Sodium bread, cherry tomatoes, avocado, and bananas. Described as a quick sandwich. Source: Sandwiches & Pita Pockets, page 23

Other sandwich recipes involve grilling or preparing wraps on a griddle, which require cooking.

**Assessment:**
- Retrieval quality: Poor — scores are all low (0.60-0.62); the system failed to retrieve the no-cook recipes that are present in the corpus (e.g., Edamame & Hazelnuts, Jicama Chips, multiple assembly-style sandwiches)
- Answer quality: Poor — the meal planning query inherently requires retrieving 5+ no-cook recipes to be useful; returning only 1 makes the answer not actionable
- Was the right context retrieved? No
- If not, what was missing? "No cooking" is a metadata attribute (cooking_method: no-cook) not well-captured by semantic embedding alone; the query requires either metadata filtering or increasing top-k significantly. The concept "quick weekday" also didn't match any text in the recipe cards.

---

## Query 8: What are good recipes for an Indian themed dinner?

**Question:** What are good recipes for an Indian themed dinner?

**Retrieved Chunks:**
1. `Potato Pumpkin Bhakri` by Kiran Sharma (score: 0.6594) — Savory Pancakes & Waffles
2. `Jowar Brown Rice Mathri` by Mrs N K Manku (score: 0.6475) — Savory Snacks
3. `Aloo Tikki Chaat` by Shalini Priyadarshini (score: 0.6455) — Savory Snacks
4. `Kala Chana Chaat` by Kusum Dhairyawan (score: 0.6381) — Savory Snacks
5. `Kathi Rolls` by Sharmila Vedam (score: 0.6380) — Sandwiches & Pita Pockets

**Generated Answer:**
Here are some WFPB recipes from Thankful2Plants.com for an Indian themed dinner:

- **Potato Pumpkin Bhakri** by Kiran Sharma — Indian bread (Bhakri) with grated pumpkin, tiger nut flour, spices. Source: Savory Pancakes & Waffles, page 7
- **Jowar Brown Rice Mathri** by Mrs N K Manku — Savory Indian snack (Mathri) with jowar flour, amchoor, asafoetida, carom seeds. Source: Savory Snacks, page 56
- **Aloo Tikki Chaat** by Shalini Priyadarshini — Mashed potato-kala chana patties pan-fried as chaat with soy yogurt and chutneys. Source: Savory Snacks, page 31
- **Kala Chana Chaat** by Kusum Dhairyawan — boiled kala chana with fresh vegetables, Mint-Cilantro Chutney, Date Tamarind Chutney. Source: Savory Snacks, page 24
- **Kathi Rolls** by Sharmila Vedam — Sweet Potato Paratha with air-fried tandoori tofu, Green Chutney. Source: Sandwiches & Pita Pockets, page 41

**Assessment:**
- Retrieval quality: Good — all 5 retrieved recipes are indeed Indian cuisine; thematic queries with broad cultural categories work well
- Answer quality: Good — all 5 recipes are described with relevant details and correct attribution
- Was the right context retrieved? Yes
- Notes: The corpus is predominantly Indian WFPB recipes so this query naturally performs well; scores are moderate (0.64-0.66) rather than high because "Indian themed dinner" does not match specific text in recipe cards — the system is using semantic inference effectively here

---

## Query 9: Which recipes use fermented ingredients like miso or natto?

**Question:** Which recipes use fermented ingredients like miso or natto?

**Retrieved Chunks:**
1. `Chinese Gnocchi in Mushroom Sauce` by Frank Lee (score: 0.6400) — Tikkis, Cutlets, Falafel, Dumplings
2. `Simple Shakarkandi` by Gurmeet Manku (score: 0.6317) — Savory Snacks
3. `Kathi Rolls` by Sharmila Vedam (score: 0.6308) — Sandwiches & Pita Pockets
4. `Yum Cha` by Frank Lee (score: 0.6295) — Tikkis, Cutlets, Falafel, Dumplings
5. `Tofu Banh Mi` by Leena Menon (score: 0.6293) — Sandwiches & Pita Pockets

**Generated Answer:**
The context does not contain any recipes that specifically use miso or natto. However, some recipes include other fermented ingredients:

- **Kathi Rolls** by Sharmila Vedam — uses homemade soy yogurt
- **Yum Cha** by Frank Lee — uses tamari and sriracha
- **Tofu Banh Mi** by Leena Menon — uses low sodium soy sauce and Sriracha Sauce

**Assessment:**
- Retrieval quality: Partial — the system retrieved recipes with loosely fermented-adjacent ingredients (soy sauce, tamari) but missed the specific miso/natto angle; the corpus likely has no miso/natto recipes, but the retrieval couldn't confirm this
- Answer quality: Good — the LLM honestly stated that miso/natto are absent and pivoted to the closest available alternatives (soy-based fermented condiments), which is a reasonable response
- Was the right context retrieved? Partially — no true miso/natto recipes in corpus; system retrieved the best available approximations
- Notes: The low similarity scores (all ~0.63) indicate this is a sparse/absent topic in the corpus; honest "not found" with alternatives is the correct behavior

---

## Query 10: What breakfast or porridge recipes are available?

**Question:** What breakfast or porridge recipes are available?

**Retrieved Chunks:**
1. `Savory Pancakes & Waffles — Whole Food Plant-Based` by Gurmeet Manku (score: 0.6352) — Savory Pancakes & Waffles
2. `Okra Tofu Pancakes` by Frank Lee (score: 0.6278) — Savory Pancakes & Waffles
3. `Soybean Pancakes` by Frank Lee (score: 0.6273) — Savory Pancakes & Waffles
4. `Millet Moong Pesarattu` by Leena Menon (score: 0.6161) — Savory Pancakes & Waffles
5. `Chinese Veggie Potato Pancakes` by Frank Lee (score: 0.6153) — Savory Pancakes & Waffles

**Generated Answer:**
The provided context does not contain any recipes explicitly categorized as 'breakfast' or 'porridge.' However, there are several pancake and waffle recipes available from Thankful2Plants.com, which are often enjoyed for breakfast:

- **Savory Pancakes & Waffles — Whole Food Plant-Based** by Gurmeet Manku — overview of Adai, Cheela, Uttapam, Pesarattu, Handvo, Chickpea Omelette, Savory Pancakes, Savory Waffles. Source: page 1
- **Okra Tofu Pancakes** by Frank Lee — okra, tofu, flax seed egg replacer, carrot, spring onions, soy sauce. Source: page 35
- **Soybean Pancakes** by Frank Lee — soybeans soaked and blended into batter with blueberries and strawberries. Source: page 36
- **Millet Moong Pesarattu** by Leena Menon — whole green moong, millets, fermented overnight batter, oil-free griddle. Source: page 25
- **Chinese Veggie Potato Pancakes** by Frank Lee — potato dough fermented, with zucchini, carrots, roasted on non-stick pan. Source: page 37

**Assessment:**
- Retrieval quality: Good — retrieved 5 breakfast-appropriate savory pancake recipes; the corpus has a "Sweet Porridge" PDF but the Week 1 test set used the Savory Pancakes PDF, and results correctly come from there
- Answer quality: Good — LLM correctly noted the corpus doesn't use "breakfast" as a label while still surfacing the most relevant results
- Was the right context retrieved? Yes — pancake recipes are the closest match available in the indexed PDFs
- Notes: The corpus uses WFPB category names (Savory Pancakes & Waffles) rather than "breakfast" — queries using WFPB vocabulary will outperform general food vocabulary queries

---

## Summary of Patterns

| Query | Type | Retrieval | Answer | Notes |
|-------|------|-----------|--------|-------|
| What recipes can I make with avocado and tomato? | Ingredient (multi) | Good | Good | LLM correctly filters irrelevant chunks |
| Show me recipes that use edamame | Ingredient (single) | Good | Good | Only 1 edamame recipe exists across 4 PDFs |
| What recipes did Sirisha Potluri create? | Creator (shorthand name) | Partial | Partial | Short name "Sirisha Potluri" misses some recipes |
| Show me recipes by Dr Sirisha Potluri | Creator (full title) | Good | Good | Full "Dr" prefix improves recall significantly |
| How do I make Walnut Mushroom Pate? | Named recipe / how-to | Good | Good | Highest score (0.8061); specific name queries excel |
| What is the cooking strategy for Tofu Banh Mi? | Strategy / named recipe | Good | Good | Highest score overall (0.8323) |
| Suggest quick weekday lunch ideas with no cooking | Meal planning / filter | Poor | Poor | No-cook filtering needs metadata; top-k too low |
| What are good recipes for an Indian themed dinner? | Thematic / cultural | Good | Good | Corpus is predominantly Indian; works well |
| Which recipes use fermented ingredients like miso or natto? | Thematic / ingredient | Partial | Good | Miso/natto absent; LLM gracefully pivoted to alternatives |
| What breakfast or porridge recipes are available? | Category / meal type | Good | Good | WFPB vocab mismatch (breakfast vs Savory Pancakes) caught by LLM |

# Production Decisions Document

## 1. Production Assessment Summary

For this Capstone project, I prioritized features that address the specific behaviors of personal blog readers interacting with Gurmeet Manku's Thankful2Plants recipe collection:

- **Conversation Memory (Critical)**: Week 4's follow-up evaluations showed significant degradation when users didn't explicitly name the recipe they were asking about in secondary turns. Implementing cross-turn memory was paramount.
- **Query Routing (Critical)**: Different requests require distinctly different system prompts. "How-to" requests require ordered steps, whereas thematic searches ("recipes with avocado") require short lists.
- **Semantic Caching (Recommended)**: Personal blogs often experience duplicate traffic paths for their "hero" content (e.g., Ezekiel Sandwich). Reducing redundant LLM calls and API latency directly improves the user experience.
- **Observability (Optional)**: While tracing (e.g., Opik) would be nice, the priority was building a robust service backbone. I skipped Opik integration to focus on dockerizing the pipeline in a reproducible manner.

## 2. Prompt Template Design

I identified four specific query types suited to this corpus:

- `FACTUAL`: Standard RAG retrieval searching for themes, ingredients, or creators. Format requires concise bullet points.
- `HOW_TO`: Procedural requests. Format relies on numbered steps and clear instructional tone.
- `COMPARISON`: Contrasting different recipes or cooking styles. Format relies on markdown tables or comparative lists.
- `PLAN`: Meal planning requests. Format requires organizing suggestions by days or events.

The **Classification Prompt** categorizes queries using few-shot learning directly mapped to these actual queries from our Week 4 golden dataset. I explicitly tailored the "Role" string from the generic course system prompt to: *"You are a knowledgeable Whole Food Plant-Based (WFPB) cooking assistant."*

## 3. Services Implemented

| Service | Implemented? | Configuration | Why This Configuration |
|---|---|---|---|
| Conversation Memory | Yes | Redis List, `gemini-2.5-flash` for rewriting | Flash is fast and cheap enough for rewriting. Redis persists sessions efficiently even if the backend container restarts. |
| Semantic Cache | Yes | Redis HNSW `voyage-3-large` threshold `0.60` | We use cosine distance. Setting the threshold at a medium conservativeness (0.60) catches syntactic rephrases without returning false positives on different ingredient questions. |
| Query Routing | Yes | 4 custom types, `FACTUAL` fallback | Resolves conflicting format requests. Fallback to FACTUAL ensures standard keyword searches still format correctly. |
| Observability | No | N/A | Skipped to focus on containerization and foundational deployment architecture. |

## 4. Services Skipped

**Observability (Opik)**: 
I decided NOT to implement observability via third-party telemetry tools at this stage. 
*Why:* For a single-user proof-of-concept focused on core RAG integration, local application logging is sufficient. The current failure modes are more likely to be architectural (e.g., Redis disconnects) than obscure prompt regressions.
*When to add later:* As the service goes live to Gurmeet's public, setting up Opik will be necessary to track which recipes get searched the most and where the LLM hallucinates, enabling better prompt refinements down the line.

## 5. Deployment Architecture

- **Containerization**: We use a `docker-compose.yml` multi-service orchestration bridging:
  1. A `redis/redis-stack-server:latest` context wrapper for HNSW and Conversation structures.
  2. A `python:3.11-slim` image using `uv` for lightning-fast dependency management running a Uvicorn ASGI server.
- **Managed Services**: The system depends on Qdrant Cloud for persistent vector storage and Voyage/Google AI via their respective APIs.
- **Why local Compose initially**: To iron out network bridging between the newly formed semantic caching systems and the REST endpoints before a public release on generic PaaS (like Railway).

## 6. What You Would Change at Scale

If the system expanded from 1 test user to 1000 daily blog visitors:

1. **Configurations to change**: The Redis Semantic Cache TTL would be dropped from 24 hours to something shorter (e.g., 2 hours) or cache invalidation schemes would be required whenever Gurmeet uploads new recipe PDFs, to ensure users aren't served stale meal plans.
2. **Critical Services**: Observability transitions from optional to critical. We'd absolutely need Opik active to map User Session failure rates. Feedback collection (thumbs up/down) in the hypothetical UI would directly pipe to our prompt refinements.
3. **First Monitoring Target**: The cache hit rate. If the semantic distance threshold (0.60) is poorly calibrated, we could either be missing 90% of cache opportunities (costing tokens) or serving wildly inaccurate overlaps (destroying trust). Monitoring the `distance_threshold` vs. `cache_hit_rate` would be the highest priority.

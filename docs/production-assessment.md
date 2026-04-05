# Production Needs Assessment: WFPB Recipe RAG

## Feature Assessment

| Feature | What It Does | Critical for Your Project? | Why / Why Not |
|---|---|---|---|
| **Conversation memory** | Resolves follow-up references across turns | **Critical** | Users often ask follow-up questions about cooking steps or alternatives (e.g., "What if I don't have X?"). |
| **Semantic caching** | Sub-50ms responses for repeated/similar queries | **Recommended** | High-volume popular recipes (e.g., "whole wheat sandwich") can save cost and latency. |
| **Query routing** | Type-specific prompt templates (factual, how-to, troubleshooting, code) | **Critical** | Procedural cooking instructions need numbered steps; search results need a concise list of names and links. |
| **Observability** | Tracing every pipeline step, monitoring quality over time | **Recommended** | To identify failures in extraction/retrieval before the user sees them. |
| **Feedback collection** | Users rate answers, ratings feed back into improvement | **Optional** | This is a personal blog assistant, so large-scale feedback is a low priority vs. accuracy. |

## Constraint Checklist

Check all that apply to your project:

- [x] **Multi-turn use case**: Users will ask follow-up questions that reference previous answers (e.g., "Add that to my meal plan").
- [x] **Repeated query patterns**: Users frequently ask for the same or similar staple recipes (Idli, Dal, etc.).
- [x] **Multiple query types**: Your corpus serves factual lookups (ingredients), procedures (how-to), and troubleshooting (what-if).
- [x] **Latency budget matters**: Users expect fast responses; repeated queries should be near-instant.
- [ ] **Quality monitoring needed**: You need to track answer quality over time, not just at evaluation time.
- [x] **User-facing application**: The system will be used by people other than you (Gurmeet's blog readers).
- [x] **Deployment required**: The system needs to run on a server (Railway/Render) reachable via the blog.

## Decision Guide Rationale

- **Implement conversation memory**: My follow-up query tests (from Week 4) showed that many questions rely on context (e.g., "Give me the recipe for that").
- **Implement semantic caching**: To handle the Pareto distribution of recipe requests and keep costs low.
- **Implement query routing**: A one-size-fits-all prompt doesn't distinguish between "Plan a week of lunches" and "How much salt in the dal?".
- **Containerize with Docker**: For reproducible deployment matching the course standards.

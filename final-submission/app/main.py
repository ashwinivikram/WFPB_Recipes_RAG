import os
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
from dotenv import load_dotenv

from google import genai
import voyageai
from fastembed import SparseTextEmbedding
from qdrant_client import QdrantClient

# Load env variables (e.g. API keys)
load_dotenv()

# We can reuse the retrieval pipeline from week 3
from scripts.09_rag_with_rerank import retrieve_and_rerank, build_context

# Import our new production services
from app.services.conversation import ConversationMemory
from app.services.semantic_cache import SemanticCache
from app.services.query_router import QueryRouter

app = FastAPI(title="WFPB Recipe Production RAG")

# 1. Initialize Clients
gemini = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
vo = voyageai.Client(api_key=os.getenv("VOYAGE_API_KEY"))
qdrant = QdrantClient(url=os.getenv("QDRANT_URL"), api_key=os.getenv("QDRANT_API_KEY"))
sparse_model = SparseTextEmbedding("Qdrant/bm25")

# 2. Initialize Services
redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
memory = ConversationMemory(redis_url=redis_url, gemini_client=gemini)
cache = SemanticCache(redis_url=redis_url, voyage_client=vo)
router = QueryRouter(gemini_client=gemini)

class QueryRequest(BaseModel):
    query: str
    session_id: str = "default_session"
    creator_filter: str | None = None

@app.post("/query")
def query_rag(request: QueryRequest):
    # Step 1: Conversation Memory (Rewrite)
    rewritten_query = memory.rewrite_if_needed(request.session_id, request.query)
    
    # Step 2: Semantic Cache
    cached_answer = cache.check(rewritten_query)
    if cached_answer:
        # Save this interaction to memory and return cache hit
        memory.add_turn(request.session_id, request.query, cached_answer)
        return {
            "answer": cached_answer, 
            "source": "cache", 
            "rewritten_query": rewritten_query
        }
    
    # Step 3: Query Routing
    q_type = router.route(rewritten_query)
    
    # Step 4: Retrieval and Reranking (Using our best pipeline from week 3)
    chunks = retrieve_and_rerank(
        query=rewritten_query,
        qdrant=qdrant,
        vo=vo,
        sparse_model=sparse_model,
        creator_filter=request.creator_filter
    )
    context = build_context(chunks)
    
    # Step 5: Generation using the routed template
    final_prompt = router.build_prompt(q_type, context, rewritten_query)
    try:
        resp = gemini.models.generate_content(
            model="gemini-2.5-flash",
            contents=final_prompt
        )
        answer = resp.text
    except Exception as e:
        answer = f"Error generating answer: {e}"
        q_type = "ERROR"

    # Save to Cache and Memory
    if answer and q_type != "ERROR":
        cache.store(rewritten_query, answer)
        memory.add_turn(request.session_id, request.query, answer)
    
    return {
        "answer": answer,
        "source": "generation",
        "query_type": q_type,
        "rewritten_query": rewritten_query
    }

@app.get("/health")
def health():
    return {"status": "healthy"}

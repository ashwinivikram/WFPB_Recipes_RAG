import redis
import voyageai
import numpy as np
from redis.commands.search.field import VectorField, TextField
from redis.commands.search.query import Query
from redis.commands.search.indexDefinition import IndexDefinition, IndexType
from redis.exceptions import ResponseError

class SemanticCache:
    def __init__(self, redis_url: str, voyage_client: voyageai.Client, namespace: str = "cache", distance_threshold: float = 0.60, ttl: int = 86400):
        # We use a threshold around 0.60 to 0.70 for cosine distance depending on the embeddings. 0.08 might be too tight. We can adjust later.
        self.redis = redis.from_url(redis_url)
        self.voyage = voyage_client
        self.namespace = namespace
        self.distance_threshold = distance_threshold
        self.ttl = ttl
        self.embed_model = "voyage-3-large"
        self.dim = 1024 # Voyage-3-large dimension
        self.index_name = f"{self.namespace}_idx"
        self._setup_index()

    def _setup_index(self):
        try:
            self.redis.ft(self.index_name).info()
        except ResponseError:
            # Create index for HNSW vector search
            schema = (
                TextField("answer"),
                VectorField("embedding", "HNSW", {"TYPE": "FLOAT32", "DIM": self.dim, "DISTANCE_METRIC": "COSINE"})
            )
            definition = IndexDefinition(prefix=[self.namespace + ":"], index_type=IndexType.HASH)
            try:
                self.redis.ft(self.index_name).create_index(fields=schema, definition=definition)
            except Exception as e:
                print(f"Warning: Failed to create Redis index. RediSearch might not be available: {e}")

    def check(self, query: str) -> str | None:
        try:
            # Embed query
            emb = self.voyage.embed([query], model=self.embed_model, input_type="query").embeddings[0]
            emb_bytes = np.array(emb, dtype=np.float32).tobytes()

            # Search Redis
            q = Query(f"*=>[KNN 1 @embedding $vec AS distance]").return_fields("answer", "distance").sort_by("distance").dialect(2)
            res = self.redis.ft(self.index_name).search(q, {"vec": emb_bytes})
            
            if res.docs:
                dist = float(res.docs[0].distance)
                if dist < self.distance_threshold:
                    return res.docs[0].answer
            return None
        except Exception as e:
            print(f"Cache check error: {e}")
            return None

    def store(self, query: str, answer: str):
        try:
            emb = self.voyage.embed([query], model=self.embed_model, input_type="query").embeddings[0]
            emb_bytes = np.array(emb, dtype=np.float32).tobytes()
            
            key = f"{self.namespace}:{hash(query)}"
            self.redis.hset(key, mapping={"answer": answer, "embedding": emb_bytes})
            self.redis.expire(key, self.ttl)
        except Exception as e:
            print(f"Cache store error: {e}")

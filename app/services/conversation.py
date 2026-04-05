import json
import redis
from google import genai
from app.prompts.templates import REWRITE_SYSTEM_PROMPT

class ConversationMemory:
    def __init__(self, redis_url: str, gemini_client: genai.Client, namespace: str = "conv", window_size: int = 10):
        self.redis = redis.from_url(redis_url)
        self.gemini = gemini_client
        self.namespace = namespace
        self.window_size = window_size
        self.rewrite_model = "gemini-2.5-flash"

    def get_history(self, session_id: str) -> list:
        key = f"{self.namespace}:{session_id}"
        lines = self.redis.lrange(key, 0, -1)
        return [json.loads(line) for line in lines]

    def add_turn(self, session_id: str, query: str, answer: str):
        key = f"{self.namespace}:{session_id}"
        turn = json.dumps({"query": query, "answer": answer})
        self.redis.rpush(key, turn)
        # trim to window size
        self.redis.ltrim(key, -self.window_size, -1)

    def rewrite_if_needed(self, session_id: str, current_query: str) -> str:
        history = self.get_history(session_id)
        if not history:
            return current_query

        # Build conversation string
        conv_str = ""
        for h in history:
            conv_str += f"User: {h['query']}\nAssistant: {h['answer']}\n"
        
        prompt = f"Conversation History:\n{conv_str}\n\nFollow-up question: {current_query}"
        
        resp = self.gemini.models.generate_content(
            model=self.rewrite_model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                system_instruction=REWRITE_SYSTEM_PROMPT,
                temperature=0.0
            )
        )
        return resp.text.strip()

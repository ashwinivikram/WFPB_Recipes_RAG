import json
from google import genai
from app.prompts.templates import CLASSIFICATION_PROMPT, TEMPLATES

class QueryRouter:
    def __init__(self, gemini_client: genai.Client):
        self.gemini = gemini_client
        self.model = "gemini-2.5-flash"

    def route(self, query: str) -> str:
        try:
            resp = self.gemini.models.generate_content(
                model=self.model,
                contents=query,
                config=genai.types.GenerateContentConfig(
                    system_instruction=CLASSIFICATION_PROMPT,
                    temperature=0.0,
                    response_mime_type="application/json"
                )
            )
            parsed = json.loads(resp.text)
            category = parsed.get("category", "FACTUAL")
            if category not in TEMPLATES:
                return "FACTUAL"
            return category
        except Exception as e:
            print(f"Routing error: {e}")
            return "FACTUAL"

    def build_prompt(self, query_type: str, context: str, query: str) -> str:
        sys_prompt = TEMPLATES.get(query_type, TEMPLATES["FACTUAL"])
        return f"{sys_prompt}\n\nContext:\n{context}\n\nQuestion: {query}"

from ollama import Client

class AIService:
    def __init__(
        self,
        host: str = "http://localhost:11434",
    ):
        self.client = Client(host=host, timeout=120) # Ollama client with a 120-second timeout
        self.chat_model = "llama3.2"
        self.embedding_model = "embeddinggemma"

    def generate_answer(self, question: str) -> str:
        response = self.client.chat(
            model=self.chat_model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a helpful AI assistant. "
                        "Explain technical topics clearly."
                    ),
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
        )

        return response.message.content or ""

    def generate_embeddings(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        response = self.client.embed(
            model=self.embedding_model,
            input=texts,
        )

        return [
            list(vector)
            for vector in response.embeddings
        ]


ai_service = AIService()

def get_ai_service() -> AIService:
    return ai_service

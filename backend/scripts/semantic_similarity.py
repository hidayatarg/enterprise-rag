
from math import sqrt

from app.ai_service import AIService


def cosine_similarity(
    a: list[float],
    b: list[float],
) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sqrt(sum(x * x for x in a))
    norm_b = sqrt(sum(y * y for y in b))

    if not norm_a or not norm_b:
        raise ValueError("Cannot compare zero vectors")

    if len(a) != len(b):
        raise ValueError("Vector dimensions differ")

    return dot / (norm_a * norm_b)


def main():
    sentences = [
        "A customer wants a payment refund.",
        "A buyer is requesting their money back.",
        "The weather will be sunny tomorrow.",
    ]

    service = AIService()

    vectors = service.generate_embeddings(sentences)

    print(f"Embedding dimensions: {len(vectors[0])}")

    for i in range(1, len(sentences)):
        score = cosine_similarity(
            vectors[0],
            vectors[i],
        )

        print(
            f"Similarity between sentence 1 "
            f"and sentence {i + 1}: {score:.4f}"
        )


if __name__ == "__main__":
    main()

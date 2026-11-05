# A PDF may contain 20,000 characters, but embedding that entire document as one vector is rarely
# useful for precise question answering. Instead, we'll create smaller, overlapping text chunks.


from dataclasses import dataclass
from io import BytesIO

import pymupdf


@dataclass(frozen=True)
class TextChunk:
    content: str
    page_number: int # The page number from which the chunk was extracted forex: According to payment-policy.pdf, page 4, refunds must be approved.
    chunk_index: int


def split_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 200,
) -> list[str]:
    if chunk_size <= 0 or not 0 <= overlap < chunk_size:
        raise ValueError("Invalid chunk settings")

    text = " ".join(text.split())

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + chunk_size, len(text))

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        if end == len(text):
            break

        start = end - overlap

    return chunks


def extract_pages(
    data: bytes,
    filename: str,
) -> list[tuple[int, str]]:
    if filename.lower().endswith(".pdf"):
        with pymupdf.open(
            stream=BytesIO(data),
            filetype="pdf",
        ) as pdf:
            return [
                (page_number, page.get_text()) # get_text() extracts text from PDF pages
                for page_number, page in enumerate(pdf, start=1)
            ]

    if filename.lower().endswith(".txt"):
        return [(1, data.decode("utf-8"))]

    raise ValueError("Unsupported document type")


def process_document(
    data: bytes,
    filename: str,
) -> list[TextChunk]:
    pages = extract_pages(data, filename)

    chunks = []

    for page_number, text in pages:
        for content in split_text(text):
            chunks.append(
                TextChunk(
                    content=content,
                    page_number=page_number,
                    chunk_index=len(chunks),
                )
            )

    return chunks

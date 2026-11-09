
from pydantic import BaseModel, Field

class EvidenceCitation(BaseModel):
    reference: int = Field(ge=1)
    quote: str = Field(min_length=1)


class GroundedAnswer(BaseModel):
    answer: str
    sufficient_evidence: bool
    citations: list[EvidenceCitation]

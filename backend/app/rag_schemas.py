
from pydantic import BaseModel, Field, model_validator


class EvidenceCitation(BaseModel):
    reference: int = Field(
        ge=1,
        description="The numbered source being cited.",
    )

    quote: str = Field(
        min_length=1,
        description="Exact quotation from the cited document.",
    )


class GroundedAnswer(BaseModel):
    answer: str = Field(
        min_length=1,
        description="Answer based on retrieved document evidence.",
    )

    sufficient_evidence: bool = Field(
        description="Whether the evidence supports an answer.",
    )

    citations: list[EvidenceCitation] = Field(
        description="Supporting source citations.",
    )

    @model_validator(mode="after")
    def validate_evidence_consistency(self):
        if self.sufficient_evidence and not self.citations:
            raise ValueError(
                "Sufficient evidence requires at least one citation"
            )

        if not self.sufficient_evidence and self.citations:
            raise ValueError(
                "Insufficient evidence cannot include citations"
            )

        return self

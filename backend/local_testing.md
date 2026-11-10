`Sample-policy.txt` will be used to test the RAG system. It contains a sample policy document that can be used to test the retrieval and question-answering capabilities of the system.



Start FastAPI

```bash
uvicorn app.main:app --reload --port 8000
uv run python -m uvicorn app.main:app --reload --port 8000
```

Synchronize dependencies

```bash
uv sync
```

Run tests
```bash
uv run python -m pytest tests/ -v
```

The script runs eight real question embeddings and compares the two retrieval configurations.
```bash
uv run python -m evaluation.run_retrieval_eval \
  --document-id d0d60e85-28bf-4255-9e3c-d04a29e2d801 \
  --k 5
```
#### Results 
#
Dataset: refund_policy_v1

Document ID: d0d60e85-28bf-4255-9e3c-d04a29e2d801

Stored chunks: 1

K: 5


[refund_001] How long does it take to process approved refunds?
  
  baseline: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00
  production: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00

[refund_002] When can customers request a refund?
  
  baseline: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00
  production: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00

[refund_003] Do refunds above $500 require manager approval?
  
  baseline: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00
  production: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00

[refund_004] Does a $300 refund require manager approval under the stated threshold?
  
  baseline: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00
  production: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00

[refund_005] What information is required for a refund request?
  
  baseline: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00
  production: Hit@5=1.00 | Recall@5=1.00 | RR@5=1.00

[refund_006] What is the CEO's annual salary?
  
  baseline: 1 candidates (unanswerable; no Recall/MRR)
  production: 0 candidates (unanswerable; no Recall/MRR)

[refund_007] What is the company's headquarters address?
  
  baseline: 1 candidates (unanswerable; no Recall/MRR)
  production: 0 candidates (unanswerable; no Recall/MRR)

[refund_008] Which bank processes the refunds?
  
  baseline: 1 candidates (unanswerable; no Recall/MRR)
  production: 1 candidates (unanswerable; no Recall/MRR)

=== RETRIEVAL SUMMARY ===

BASELINE

Answerable cases: 5

Hit@5:    1.0000

Recall@5: 1.0000

MRR@5:    1.0000

PRODUCTION

Answerable cases: 5

Hit@5:    1.0000

Recall@5: 1.0000

MRR@5:    1.0000
#
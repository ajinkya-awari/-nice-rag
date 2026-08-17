# NICE-RAG

NICE-RAG is a CPU-friendly research demonstration for retrieving cited passages from five NICE guidelines and composing bounded research responses.

## Scope

The approved guideline scope is NG28, CG127, NG17, NG185, and CG191. The project is research information only: it is not clinical decision support, a medical device, or a substitute for qualified professional advice.

The runtime is being built incrementally with synthetic offline fixtures first. NICE PDFs, model weights, Chroma stores, credentials, patient data, and unreviewed traces remain restricted. NICE downloads, Groq calls, cloud transfer, deployment, publication, email, and Git operations are explicit gates.

## Current milestone

The repository currently contains an import-safe protocol scaffold, a synthetic ingestion contract that preserves guideline/page provenance, an approved dependency manifest, and deterministic offline tests. The manifest is recorded for later environment setup and has not been installed or resolved in these milestones.

Run the local checks from this directory:

```text
python -m compileall src tests
python -m pytest -q
python run.py "synthetic NICE scenario"
```

## Attribution

Approved public NICE-derived material must include attribution under the NICE Open Government Licence (OGL). This repository currently contains no NICE source PDFs or downloaded guideline content.

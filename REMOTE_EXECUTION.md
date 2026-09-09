# Remote execution boundary

## Open-evidence boundary — 2026-09-09

The PMC benchmark is a separate local CPU/network gate, not a NICE or provider stage. `--list-open-sources` is offline; `--fetch-open-evidence` contacts only the fixed official PMC OAI endpoint; `--validate-open-evidence` is local-only. The approved attempt and single retry ended partial after three validated records, so no further fetch is authorized by the prior gate. Kaggle is not required to resolve this blocker.

Raw PMC XML must remain ignored and private. Only sanitized metadata, hashes, counts, statuses, and citation prefixes may be public. NICE content, models, Chroma, providers, patient data, deployment, and publication remain separate closed gates.

---

NICE-RAG uses a private Kaggle kernel for one current purpose: reproduce the provider-free synthetic checks in a clean Python environment. The notebook clones only the reviewed public source revision and attaches no datasets, models, kernels, competitions, secrets, or patient data.

## Current authorized stage

Run [`notebooks/kaggle_nice_rag.ipynb`](notebooks/kaggle_nice_rag.ipynb) through the private CPU kernel described in the [Kaggle runbook](notebooks/KAGGLE_RUNBOOK_nice_rag.md). The notebook:

1. records Python, platform, input, and GPU visibility;
2. clones the existing NICE-RAG repository and records its revision;
3. installs `requirements.txt` inside Kaggle;
4. runs `compileall` and the complete synthetic pytest suite;
5. runs the 1,000-document CPU smoke and five-scenario listing;
6. scans for restricted artifacts and writes a sanitized evidence JSON file.

Every command is fail-closed. A Kaggle `COMPLETE` status is accepted only after the downloaded evidence file is inspected.

## Closed external gates

The synthetic kernel does not:

- acquire or read NICE PDFs;
- download an embedding model;
- build or load Chroma;
- read provider credentials or call Groq;
- process patient or private clinical data;
- generate live clinical answers or traces;
- upload to Hugging Face, deploy, publish, or email.

Each stage above needs a separate current approval, provenance and privacy review, and its own fail-closed evidence plan.

## Release boundary

Public source may include code, tests, synthetic fixtures, the unexecuted notebook/runbook, and sanitized evidence summaries. It must exclude raw documents, models, caches, vector stores, credentials, patient data, private traces, private Kaggle outputs, and internal planning controls.

The repository currently contains no NICE source text. NICE's UK open content licence explicitly excludes AI use; attribution or OGL language alone is not permission for RAG acquisition or processing. A corrected scope, NICE approval/licensing for the exact AI purpose and territory, third-party-rights review, and complete source provenance are required before any NICE-content stage. No software license has been approved, so the absence of a `LICENSE` file remains an explicit reuse limitation.

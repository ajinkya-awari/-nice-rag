# NICE-RAG

CPU-friendly, citation-first retrieval research scaffold for five NICE guideline scopes. The repository is intentionally staged: provenance, deterministic tools, privacy boundaries, and synthetic evaluation come before heavyweight or externally gated runtime work.

> Research information only. NICE-RAG is not clinical decision support, a medical device, or a substitute for qualified professional advice.

## Project status

| Area | Status |
| --- | --- |
| Import-safe source tree | Complete |
| Synthetic ingestion and cited retrieval | Complete |
| Offline CPU stress check | Complete |
| Five canonical fixture scenarios | Complete; live traces gated |
| NICE PDFs, embeddings, Chroma, and Groq | Deferred to authorized Kaggle/Colab work |
| Gradio/Hugging Face release | Deferred and separately gated |

Approved guideline IDs: `NG28`, `CG127`, `NG17`, `NG185`, and `CG191`.

## What is safe to run locally

The local checks use only synthetic in-memory fixtures. They do not install packages, access the network, download NICE documents or models, create Chroma, call Groq, or write result traces.

```text
python -m compileall src tests
python -m pytest -q
python run.py --list-scenarios
python run.py --cpu-smoke --documents 1000 --repeats 1
```

The CPU smoke mode exercises tagging, chunking, lexical retrieval, citation formatting, and the three-passage cap over synthetic documents. Its workload is bounded by `src/offline_cpu.py` and remains memory-only.

## Repository map

```text
src/                 import-safe runtime contracts and offline logic
tests/               dependency-free protocol, privacy, and synthetic tests
data/                empty boundary for restricted remote inputs
results/             empty boundary for reviewed outputs
run.py               local CLI for offline checks
requirements.txt     pinned environment for later remote setup
REMOTE_EXECUTION.md  Kaggle/Colab-only gated runbook
```

## External execution boundary

Storage-heavy work is documented in [`REMOTE_EXECUTION.md`](REMOTE_EXECUTION.md) for a later Kaggle or Google Colab session. Do not place PDFs, model caches, Chroma databases, credentials, patient data, or unreviewed traces in this repository. Do not run the remote stages locally.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the local-first workflow and verification checklist. New behavior should have synthetic tests first and preserve guideline/page provenance.

## Attribution

Approved public NICE-derived material must include attribution under the NICE Open Government Licence (OGL). This repository currently contains no NICE source PDFs or downloaded guideline content.

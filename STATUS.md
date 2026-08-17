# NICE-RAG status

**Last verified:** 2026-08-18 · **Branch:** `main` · **HEAD:** `9b9406f`

This is the public runtime status page. The shared portfolio workspace also contains a planning-layer `PROJECT_STATUS.md`; this runtime copy is self-contained for GitHub readers. Historical implementation plans are preserved as evidence; this file is the current done/remaining/next-action summary.

## Done

- Import-safe source tree, pinned manifest, local CLI, synthetic fixtures, and offline tests.
- Provenance-safe tagging/splitting, cited retrieval, deterministic interaction fixture, lazy runtime contracts, and privacy checks.
- Exactly five fixture-only scenarios covering NG28, CG127, NG17, NG185, and CG191.
- CPU-only synthetic stress mode: 10,000 documents, 32,000 chunks, 10 queries, valid citations, and a three-passage cap.
- GitHub README, contribution guide, issue templates, PR template, and remote-only execution runbook.

## Verification

```text
python -m pytest -q                         # 46 passed
python -m compileall src tests               # exit 0
python run.py --cpu-smoke --documents 10000 --repeats 2
# all_citations_valid=True; no files or external services used
```

## Remaining gates

NICE PDFs, dependency/model downloads, Chroma creation, Groq calls, live traces, patient data, Gradio/Hugging Face deployment, publication, and email are not done. They require an explicitly authorized Kaggle or Google Colab session and must not run locally.

## Next action

Choose Kaggle or Colab and authorize the remote stages separately. Follow [`REMOTE_EXECUTION.md`](REMOTE_EXECUTION.md). Until then, the local implementation is complete and the five scenarios remain `gated_no_live_trace`.

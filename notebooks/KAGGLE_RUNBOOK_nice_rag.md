# Kaggle runbook — NICE-RAG synthetic gate

This runbook covers only the private, provider-free synthetic kernel `ajinkya1225/19-nice-rag-validation`. It does not authorize NICE documents, model downloads, Chroma, Groq, patient data, live traces, Hugging Face, deployment, or publication.

## Staging contract

The staging directory contains exactly:

```text
kaggle_nice_rag.ipynb
kernel-metadata.json
```

`kernel-metadata.json` uses the actual notebook filename, keeps the kernel private and CPU-only, enables internet only so the notebook can shallow-clone the reviewed public repository, and declares no dataset, competition, model, or kernel sources.

The notebook checks out its literal `EXPECTED_REVISION`, so it never validates mutable GitHub `HEAD`. The provider-free path uses the existing Kaggle `pytest` installation and records that version; it does not install `requirements.txt` or any provider/model/vector/UI dependency.

## Unattended cell sequence

| Cell | Gate | Fail-closed behavior |
| --- | --- | --- |
| 1 | Scope and closed-gate notice | Markdown only |
| 2 | Environment, empty inputs, GPU visibility, source clone, exact revision checkout | Fails if any input is attached or clone/revision checkout fails |
| 3 | Existing pytest version capture | Fails if pytest is unavailable; never installs the production dependency stack |
| 4 | `compileall` and complete pytest suite | Fails on any nonzero result or missing pass count |
| 5 | 1,000-document CPU smoke and five-scenario listing | Fails on invalid citations, more than three passages, or scenario count other than five |
| 6 | Restricted-artifact scan and evidence write | Fails if a restricted artifact is present |

No manual kernel restart is required: installation and validation use fresh subprocesses of the same Python interpreter, and the notebook does not import the optional runtime packages before installation.

## CLI sequence

Run exactly once after validating staging:

```bash
kaggle kernels list --mine --page-size 1
kaggle kernels status ajinkya1225/19-nice-rag-validation
kaggle kernels push -p <private-staging-folder> -t 1800
```

Poll `kaggle kernels status ajinkya1225/19-nice-rag-validation` at short intervals for at most 30 minutes. Stop at `COMPLETE`, `ERROR`, `CANCELLED`, timeout, or missing status. Inspect logs only on failure, make one minimal correction, and retry at most once.

After `COMPLETE`, download outputs once:

```bash
kaggle kernels output ajinkya1225/19-nice-rag-validation -p <private-output-folder>
```

Accept the synthetic gate only if `nice_rag_synthetic_evidence.json` exists and records:

- source revision matching the reviewed GitHub commit;
- compile and pytest exit codes equal to zero;
- a nonzero pytest pass count;
- `documents=1000`, `max_passages=3`, and `all_citations_valid=True`;
- exactly five `gated_no_live_trace` scenarios;
- no restricted artifacts;
- all external data/model/provider/clinical/deployment stages in `skipped_gates`.

## Stop conditions

Stop immediately if the kernel is not private, belongs to another project, has attached inputs, exposes a credential, fails a command, lacks the evidence file, reports invalid citations, finds restricted artifacts, or reaches a closed gate. Do not reinterpret `COMPLETE` as proof of any NICE, model, Chroma, Groq, clinical, or deployment behavior.

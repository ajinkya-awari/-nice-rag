# Remote execution runbook

This runbook is for a later, explicitly authorized Kaggle or Google Colab session. It is intentionally not executed on the local machine. The local repository remains dependency-free and contains no NICE PDFs, model weights, vector store, credentials, patient data, or live traces.

## Upload and workspace boundary

Upload or clone only the reviewed source tree, tests, documentation, and dependency manifest. Do not upload local PDFs, Chroma directories, credentials, patient data, unreviewed traces, or notebook secrets. Keep generated restricted artifacts in the remote notebook's private storage unless a separate release review authorizes their transfer.

## Gated notebook sequence

Run the following stages only after their corresponding authorization has been granted.

1. Clone the approved repository in Kaggle or Colab and enter `nice-rag`.

   ```bash
   git clone https://github.com/ajinkya-awari/-nice-rag.git nice-rag
   cd nice-rag
   ```

2. Install the pinned environment in the remote notebook only. This is intentionally not run locally.

   ```bash
   python -m pip install -r requirements.txt
   ```

3. Acquire only the approved NICE guideline documents: NG28, CG127, NG17, NG185, and CG191. Place reviewed files in the restricted remote path `data/pdfs/`, preserving filenames that identify their guideline IDs. Do not invent URLs or use an unapproved mirror; the source acquisition procedure and authorization must be recorded before this stage.

4. Build the local remote vector store with the configured `sentence-transformers/all-MiniLM-L6-v2` embedding model and `data/chroma_db` persistence directory. Confirm that the remote runtime has enough storage before downloading dependencies or model weights. Do not copy this store back to the local machine.

5. Add `GROQ_API_KEY` as a notebook secret, never in a file or notebook cell. Invoke the gated agent only after the key and source-data gates are approved. Run exactly the five canonical scenarios from `src/scenarios.py`; preserve guideline/page citations and retain actual traces only in the approved private remote location. Never fabricate answers, citations, or traces.

## Release gate

Before any transfer, deployment, or publication, verify all of the following:

- NICE Open Government Licence attribution and the research-only disclaimer are present.
- No raw PDFs, model caches, Chroma database, secrets, patient data, or unreviewed traces are in release files.
- Exactly five actual qualitative scenario traces exist, one per canonical scenario, with no unsupported clinical or accuracy claims.
- Any Hugging Face upload or Gradio deployment has separate explicit authorization.

Until those gates are approved, the only authorized next action is to run the existing offline checks locally and select Kaggle or Colab for the later remote execution.

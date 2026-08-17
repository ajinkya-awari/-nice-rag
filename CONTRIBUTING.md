# Contributing to NICE-RAG

Thank you for helping improve this research scaffold. Contributions should keep the project reproducible, citation-first, and safe to inspect without external data.

## Local-first rules

- Use synthetic fixtures for tests and examples.
- Do not add NICE PDFs, model weights, Chroma databases, credentials, patient data, or unreviewed traces.
- Do not call Groq or another external API from tests.
- Keep optional LangChain, embedding, vector-store, and UI imports lazy.
- Preserve `guideline_id`, page metadata, the `[GUIDELINE_ID, p.PAGE]` citation format, and the five-scenario scope.

## Development loop

1. Add a focused failing test.
2. Implement the smallest local change that satisfies it.
3. Run the focused test and the complete offline suite.
4. Run compile, CLI, diff, and restricted-artifact checks.
5. Update `HANDOVER.md` with evidence and residual risks.

```text
python -m compileall src tests
python -m pytest -q
python run.py --cpu-smoke --documents 1000 --repeats 1
git diff --check
```

The pinned dependencies in `requirements.txt` are for a later authorized remote environment. They are not required for the synthetic offline suite.

## Pull requests

Keep changes focused, explain the authorization boundary, and state exactly which checks ran. A pull request must not claim clinical accuracy, source coverage, or model quality from synthetic fixtures alone.

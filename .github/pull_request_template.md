## Summary

<!-- What changed and why? -->

## Verification

- [ ] `python -m compileall src tests`
- [ ] `python -m pytest -q`
- [ ] `python run.py --cpu-smoke --documents 1000 --repeats 1`
- [ ] `git diff --check`
- [ ] Restricted-artifact scan completed

## Safety and scope

- [ ] Synthetic fixtures only, unless separately authorized and documented
- [ ] No credentials, patient data, PDFs, model files, Chroma databases, or unreviewed traces added
- [ ] No unsupported clinical, accuracy, or safety claims
- [ ] Any external gate is explicitly identified and remains closed unless authorized

## Handoff

<!-- Record residual risks and the next authorized action. -->

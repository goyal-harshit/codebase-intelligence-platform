# Lessons Learned

## 2026-07-02: Always verify PyPI package versions exist before pinning

**Mistake:** Pinned `tokenizers==0.23.0` in requirements.txt, but that version was never released on PyPI. The version list jumps from 0.22.2 → 0.23.0rc0 → 0.23.1 (no 0.23.0 final).

**Pattern:** When a library error says "version X.Y.Z is required", don't assume X.Y.Z exists. Check `pip index versions <package>` or the PyPI page first.

**Fix:** Instead of pinning the transitive dep (`tokenizers`), upgrade the direct dep (`transformers`) to a version compatible with what's already installed.

**Rule:** When fixing version conflicts between transitive dependencies, prefer upgrading the parent package rather than pinning the child to a specific version that may not exist.

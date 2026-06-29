"""Externalized prompt templates (Phase 4, bug #4)."""
import pytest

import prompts


def test_cypher_template_loads_and_keeps_signature_phrase():
    text = prompts.load("cypher_fewshot")
    # The router/test rely on this phrase to detect the Cypher step.
    assert "into Cypher" in text
    assert "{question}" in text  # placeholder substituted via str.replace by caller


def test_answer_template_has_placeholders():
    text = prompts.load("answer")
    for ph in ("{history}", "{question}", "{context}"):
        assert ph in text


def test_render_fills_placeholders():
    out = prompts.render("answer", history="", question="Q?", context="CTX")
    assert "Q?" in out and "CTX" in out
    assert "{question}" not in out


def test_summarize_template_renders():
    out = prompts.render("summarize", kind="file", target="a.py", context="- foo")
    assert "a.py" in out and "- foo" in out


def test_constants_match_files():
    from retrieval import ANSWER_PROMPT, CYPHER_FEWSHOT

    assert CYPHER_FEWSHOT == prompts.load("cypher_fewshot")
    assert ANSWER_PROMPT == prompts.load("answer")


def test_missing_template_raises():
    with pytest.raises(FileNotFoundError):
        prompts.load("does-not-exist")

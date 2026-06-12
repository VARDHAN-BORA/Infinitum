"""
Lightweight continuous evaluation harness — RAGAS / LangSmith pattern.

Computes two heuristic scores after every generation:

  faithfulness       — how well the answer is grounded in the retrieved context.
                       Measures what fraction of the answer's words appear in
                       the context blocks. A low score means the model may be
                       hallucinating beyond what was retrieved.

  answer_relevance   — how well the answer addresses the original question.
                       Measures what fraction of meaningful query terms appear
                       in the answer. A low score means the answer may be
                       off-topic.

Both are word-overlap proxies. In production these would be replaced with
model-based RAGAS scores (e.g. via Ragas + LangSmith tracing), but the
interface and threshold logic are identical — swap the scorer, keep the harness.
"""

import logging
import re

logger = logging.getLogger(__name__)

DRIFT_THRESHOLD = 0.7

_STOP_WORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "can", "what", "where", "when", "who",
    "how", "why", "which", "that", "this", "these", "those", "and", "or",
    "but", "in", "on", "at", "to", "for", "of", "with", "by", "from", "about",
    "not", "no", "it", "its", "i", "you", "we", "they", "he", "she",
}


def _tokenize(text: str) -> set[str]:
    return set(re.findall(r"\b[a-z]{2,}\b", text.lower()))


def _meaningful(tokens: set[str]) -> set[str]:
    return tokens - _STOP_WORDS


def compute_faithfulness(answer: str, contexts: list[str]) -> float:
    """Fraction of answer words present in any context block."""
    answer_words = _meaningful(_tokenize(answer))
    if not answer_words:
        return 0.0
    context_words = _tokenize(" ".join(contexts))
    return round(len(answer_words & context_words) / len(answer_words), 3)


def compute_answer_relevance(answer: str, query: str) -> float:
    """Fraction of meaningful query terms that appear in the answer."""
    query_words = _meaningful(_tokenize(query))
    if not query_words:
        return 1.0  # nothing to measure; assume relevant
    answer_words = _tokenize(answer)
    return round(len(query_words & answer_words) / len(query_words), 3)


def evaluate_and_log(
    query: str, answer: str, contexts: list[str]
) -> dict[str, float]:
    """
    Compute scores, log the results, and fire a warning on drift.
    Returns the scores dict so callers can attach it to traces if needed.
    """
    faithfulness = compute_faithfulness(answer, contexts)
    relevance = compute_answer_relevance(answer, query)
    scores = {"faithfulness": faithfulness, "answer_relevance": relevance}

    if faithfulness < DRIFT_THRESHOLD or relevance < DRIFT_THRESHOLD:
        logger.warning(
            "⚠️  RETRIEVAL DRIFT DETECTED: Flagging query for review. "
            "faithfulness=%.3f  answer_relevance=%.3f  query=%r",
            faithfulness,
            relevance,
            query[:120],
        )
    else:
        logger.info(
            "Eval OK — faithfulness=%.3f  answer_relevance=%.3f",
            faithfulness,
            relevance,
        )

    return scores

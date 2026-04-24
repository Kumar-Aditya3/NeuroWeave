from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import Dict, Iterable, Sequence

from .anchors import TOPIC_ANCHORS, VIBE_ANCHORS

POSITIVE_WORDS = {"calm", "happy", "growth", "focus", "hope", "progress", "joy", "steady", "learn"}
NEGATIVE_WORDS = {"angry", "sad", "dark", "stress", "anxiety", "doom", "rage", "drained", "overwhelmed"}
EMBED_DIM = 192


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _tokens(text: str) -> list[str]:
    normalized = _normalize(text)
    words = re.findall(r"[a-z0-9\-]{2,}", normalized)
    phrases = [f"{words[index]} {words[index + 1]}" for index in range(len(words) - 1)]
    return words + phrases


def _token_weight(token: str) -> float:
    if " " in token:
        return 1.65
    if len(token) >= 8:
        return 1.15
    return 1.0


def _hash_index(token: str, salt: str) -> int:
    digest = hashlib.sha256(f"{salt}:{token}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % EMBED_DIM


def _hash_vectorize(text: str) -> list[float]:
    vector = [0.0] * EMBED_DIM
    for token in _tokens(text):
        weight = _token_weight(token)
        vector[_hash_index(token, "a")] += weight
        vector[_hash_index(token, "b")] -= weight * 0.45
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: Sequence[float], right: Sequence[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


@lru_cache(maxsize=1)
def _load_sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer("all-MiniLM-L6-v2")
    except Exception:
        return None


def _encode_text(text: str) -> list[float]:
    model = _load_sentence_transformer()
    if model is None:
        return _hash_vectorize(text)
    vector = model.encode(text, normalize_embeddings=True)
    return [float(value) for value in vector]


def encode_text(text: str) -> list[float]:
    return _encode_text(text)


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    return _cosine(left, right)


def _score_anchors(text: str, anchors: Dict[str, Iterable[str]]) -> Dict[str, float]:
    encoded_text = _encode_text(text)
    scores: Dict[str, float] = {}
    for label, descriptions in anchors.items():
        anchor_vectors = [_encode_text(description) for description in descriptions]
        similarity = max(_cosine(encoded_text, anchor_vector) for anchor_vector in anchor_vectors)
        scores[label] = max(0.0, similarity)

    total = sum(scores.values())
    if total <= 0:
        return {label: 0.0 for label in anchors}
    return {label: round(value / total, 4) for label, value in scores.items()}


def _keyword_count(text: str, keyword: str) -> int:
    escaped = re.escape(keyword.lower())
    pattern = rf"(?<!\w){escaped}(?!\w)"
    return len(re.findall(pattern, text))


def keyword_classify(text: str) -> Dict[str, object]:
    from .main import TOPIC_KEYWORDS  # imported lazily to avoid circular import at module import time

    lowered = _normalize(text)
    topic_scores: Dict[str, float] = {}
    for topic, keywords in TOPIC_KEYWORDS.items():
        matches = sum(_keyword_count(lowered, word) for word in keywords)
        topic_scores[topic] = float(matches)

    total = sum(topic_scores.values())
    if total > 0:
        topic_scores = {k: round(v / total, 4) for k, v in topic_scores.items()}
    else:
        topic_scores = {k: 0.0 for k in TOPIC_KEYWORDS.keys()}
        topic_scores["unknown"] = 1.0

    return finalize_analysis(text, topic_scores)


def embedding_classify(text: str) -> Dict[str, object]:
    topic_scores = _score_anchors(text, TOPIC_ANCHORS)
    vibe_scores = _score_anchors(text, VIBE_ANCHORS)
    analysis = finalize_analysis(text, topic_scores)
    analysis["vibe_scores"] = vibe_scores
    if vibe_scores and max(vibe_scores.values()) > 0:
        analysis["vibe"] = max(vibe_scores, key=vibe_scores.get)
    analysis["embedding_preview"] = [round(value, 5) for value in _encode_text(text)[:24]]
    return analysis


def finalize_analysis(text: str, topic_scores: Dict[str, float]) -> Dict[str, object]:
    lowered = _normalize(text)
    positive_hits = sum(lowered.count(word) for word in POSITIVE_WORDS)
    negative_hits = sum(lowered.count(word) for word in NEGATIVE_WORDS)

    if positive_hits > negative_hits:
        sentiment = "positive"
    elif negative_hits > positive_hits:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    if negative_hits >= 2:
        vibe = "dark"
    elif positive_hits >= 2:
        vibe = "calm"
    elif "intense" in lowered or "binge" in lowered or "ranked" in lowered:
        vibe = "intense"
    else:
        vibe = "balanced"

    return {
        "topic_scores": topic_scores,
        "sentiment": sentiment,
        "vibe": vibe,
    }


def classify_text(text: str, classifier_mode: str = "embedding_primary") -> Dict[str, object]:
    if classifier_mode == "keyword_fallback":
        analysis = keyword_classify(text)
        analysis["classifier_mode"] = "keyword_fallback"
        return analysis

    analysis = embedding_classify(text)
    analysis["classifier_mode"] = "embedding_primary"
    return analysis

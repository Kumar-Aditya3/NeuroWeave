from __future__ import annotations

from collections import Counter
import math
from typing import Iterable

from .ml import classify_text, cosine_similarity, encode_text

ARC_PROTOTYPES = {
    "course grind": "studying lessons lectures notes assignments university online course exam preparation and educational focus",
    "deep work": "coding writing building debugging terminal documentation concentrated productive maker session",
    "anime binge": "anime episodes manga fandom character arcs stylized entertainment and dramatic immersion",
    "gaming streak": "competitive game sessions ranked play action reflexes match focus and intense gameplay",
    "doomscroll": "heavy news social feeds constant updates political drama anxiety and repetitive scrolling",
    "creative reset": "reflective philosophy self-help journaling visual inspiration ambient focus and calm recovery",
}


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _weighted_centroid_update(current: list[float], incoming: list[float], learning_rate: float) -> list[float]:
    merged = [((1.0 - learning_rate) * left) + (learning_rate * right) for left, right in zip(current, incoming)]
    return _normalize(merged)


def build_current_arcs(
    recent_payloads: Iterable[dict],
    classifier_mode: str = "embedding_primary",
    prior_centroids: dict[str, dict] | None = None,
) -> tuple[list[dict], dict[str, dict]]:
    payloads = list(recent_payloads)
    if not payloads:
        return [], {}

    prototype_vectors = {name: _normalize(encode_text(prompt)) for name, prompt in ARC_PROTOTYPES.items()}
    buckets: dict[str, list[dict]] = {name: [] for name in ARC_PROTOTYPES}
    centroid_state: dict[str, dict] = {}
    for arc_name, prototype in prototype_vectors.items():
        stored = (prior_centroids or {}).get(arc_name, {})
        stored_centroid = stored.get("centroid")
        if isinstance(stored_centroid, list) and stored_centroid:
            centroid = _normalize([float(value) for value in stored_centroid])
        else:
            centroid = prototype
        centroid_state[arc_name] = {
            "centroid": centroid,
            "sample_count": float(stored.get("sample_count", 0.0)),
        }

    for index, payload in enumerate(payloads):
        text_blob = " ".join(
            [
                payload.get("title", ""),
                payload.get("url", ""),
                payload.get("selected_text", ""),
                payload.get("content_text", ""),
                payload.get("source", ""),
                payload.get("event_type", ""),
                payload.get("category", ""),
                f"{payload.get('duration_seconds', 0)} seconds active",
            ]
        ).strip()
        if not text_blob:
            continue
        encoded = _normalize(encode_text(text_blob))
        arc_name = max(
            centroid_state,
            key=lambda key: cosine_similarity(encoded, centroid_state[key]["centroid"]),
        )
        analysis = classify_text(text_blob, classifier_mode=classifier_mode)
        duration_bonus = min(0.75, float(payload.get("duration_seconds", 0) or 0) / 900.0)
        recency_weight = max(0.2, 1.0 - (index * 0.035)) + duration_bonus
        sample_count = float(centroid_state[arc_name]["sample_count"])
        learning_rate = min(0.45, (0.08 + (0.22 * recency_weight)) / (1.0 + (sample_count * 0.02)))
        centroid_state[arc_name]["centroid"] = _weighted_centroid_update(
            centroid_state[arc_name]["centroid"],
            encoded,
            learning_rate,
        )
        centroid_state[arc_name]["sample_count"] = sample_count + recency_weight
        buckets[arc_name].append(
            {
                "title": payload.get("title", ""),
                "analysis": analysis,
                "weight": recency_weight,
                "category": payload.get("category", "") or payload.get("event_type", ""),
            }
        )

    arcs = []
    centroid_updates: dict[str, dict] = {}
    for arc_name, items in buckets.items():
        if not items:
            continue

        topic_counter = Counter()
        vibe_counter = Counter()
        keyword_counter = Counter()
        strength = 0.0
        sample_titles = []
        for item in items:
            strength += item["weight"]
            topic = max(item["analysis"]["topic_scores"], key=item["analysis"]["topic_scores"].get)
            topic_counter[topic] += item["weight"]
            vibe_counter[str(item["analysis"]["vibe"])] += item["weight"]
            keyword_counter[item["category"] or topic] += 1
            if len(sample_titles) < 3 and item["title"]:
                sample_titles.append(item["title"][:56])

        arcs.append(
            {
                "name": arc_name,
                "strength": round(strength, 4),
                "dominant_topic": topic_counter.most_common(1)[0][0],
                "vibe": vibe_counter.most_common(1)[0][0],
                "keywords": [keyword for keyword, _count in keyword_counter.most_common(3)],
                "sample_titles": sample_titles,
            }
        )
        centroid_updates[arc_name] = {
            "centroid": centroid_state[arc_name]["centroid"],
            "sample_count": centroid_state[arc_name]["sample_count"],
            "dominant_topic": topic_counter.most_common(1)[0][0],
            "vibe": vibe_counter.most_common(1)[0][0],
            "strength": round(strength, 4),
        }

    arcs.sort(key=lambda arc: arc["strength"], reverse=True)
    return arcs[:4], centroid_updates

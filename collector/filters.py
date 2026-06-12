"""Filtros de relevancia y pre-score por reglas."""

from __future__ import annotations

import logging
from datetime import date

from .config import (EXCLUDE_KEYWORDS, INCLUDE_KEYWORDS, PRIORITY_AGENCIES,
                     PRODUCT_MAP, RULE_SCORE_THRESHOLD)
from .sources.base import Tender, normalize, today_art

log = logging.getLogger("radar.filters")

_INCLUDE_NORM = {normalize(k): w for k, w in INCLUDE_KEYWORDS.items()}
_EXCLUDE_NORM = [normalize(k) for k in EXCLUDE_KEYWORDS]
_PRIORITY_NORM = {normalize(k): w for k, w in PRIORITY_AGENCIES.items()}
_PRODUCT_NORM = {p: [normalize(k) for k in kws] for p, kws in PRODUCT_MAP.items()}


def dedupe(tenders: list[Tender]) -> list[Tender]:
    seen, out = set(), []
    for t in tenders:
        key = t.dedup_key()
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def is_active(t: Tender, today: date | None = None) -> bool:
    """Activa = fecha de apertura estrictamente posterior a hoy."""
    today = today or today_art()
    return t.opening_date is not None and t.opening_date > today


def rule_score(t: Tender) -> Tender:
    blob = t.text_blob
    matched, score = [], 0
    for kw, weight in _INCLUDE_NORM.items():
        if kw in blob:
            matched.append(kw)
            score = max(score, weight)          # el keyword más fuerte manda
    score += min(len(matched), 4)               # bonus por densidad de señales
    for kw, boost in _PRIORITY_NORM.items():
        if kw in normalize(t.agency):
            score += boost
            break
    # exclusión: si el objeto está dominado por un rubro excluido y la señal
    # tech es débil, descartamos
    excluded_hit = any(kw in blob for kw in _EXCLUDE_NORM)
    if excluded_hit and score < 8:
        score = 0
    t.rule_score = min(score, 14)
    t.matched_keywords = matched
    # mapeo preliminar de productos
    products = []
    for product, kws in _PRODUCT_NORM.items():
        if any(kw in blob for kw in kws):
            products.append(product)
    t.products = products[:4]
    return t


def run_pipeline(tenders: list[Tender]) -> tuple[list[Tender], dict]:
    """dedupe -> activas -> tech. Devuelve candidatas ordenadas + métricas."""
    stats = {"raw": len(tenders)}
    tenders = dedupe(tenders)
    stats["deduped"] = len(tenders)
    active = [t for t in tenders if is_active(t)]
    stats["active"] = len(active)
    scored = [rule_score(t) for t in active]
    candidates = [t for t in scored if t.rule_score >= RULE_SCORE_THRESHOLD]
    candidates.sort(key=lambda t: t.rule_score, reverse=True)
    stats["candidates"] = len(candidates)
    log.info("Pipeline: %s", stats)
    return candidates, stats

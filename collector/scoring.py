"""Scoring híbrido: las reglas filtran, Claude asigna el índice de probabilidad.

Cada candidata top se manda en batch a la API de Claude, que devuelve:
  - probability: índice 0-100 de probabilidad de participación de Salesforce
  - products: productos Salesforce aplicables
  - rationale: justificación en una o dos oraciones (español)
Si no hay API key (o RADAR_DRY_RUN=1), se usa un fallback por reglas.
"""

from __future__ import annotations

import json
import logging

import requests

from .config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_TOP_N, DRY_RUN
from .sources.base import Tender

log = logging.getLogger("radar.scoring")

API_URL = "https://api.anthropic.com/v1/messages"

SYSTEM = """Sos un analista senior de preventa de Salesforce Argentina especializado \
en sector público (Nación, provincias, municipios, empresas estatales). Tu tarea: \
evaluar licitaciones públicas y estimar la probabilidad de que Salesforce pueda \
participar como proveedor (directo o vía partner/OSP como Claro Argentina).

Criterios para el índice de probabilidad (0-100):
- 85-100: CRM explícito, atención ciudadana omnicanal, contact center, agentes de IA, \
o requerimiento que mapea directo a Sales/Service Cloud o Agentforce.
- 65-84: plataforma cloud/SaaS clara, mesa de ayuda, BI con dashboards, integración \
de sistemas, desarrollo low-code.
- 40-64: transformación digital amplia donde Salesforce es contendiente real pero \
compite con desarrollo a medida u otros stacks.
- 15-39: relevancia indirecta (infraestructura TI, licencias de terceros) — sirve \
como inteligencia de cuenta más que como oportunidad directa.
- 0-14: sin encaje razonable.

Productos válidos: Sales Cloud, Service Cloud, Agentforce, Marketing Cloud, MuleSoft, \
Tableau, Salesforce Platform, Data Cloud, Field Service.

Cuentas prioritarias (subí 5-10 puntos si el organismo es PAMI/INSSJP, ANSES, ARCA, \
RENAPER, YPF, Aerolíneas, BCRA, o gobiernos provinciales con MoU activo).

Respondé SOLO con un array JSON válido, sin markdown ni texto adicional. Un objeto \
por licitación con: {"id": <int>, "probability": <int 0-100>, "products": [..], \
"rationale": "<1-2 oraciones en español rioplatense>"}."""


def _fallback(t: Tender) -> Tender:
    t.probability = min(t.rule_score * 7, 95)
    if not t.rationale:
        kws = ", ".join(t.matched_keywords[:4]) or "señales tecnológicas genéricas"
        t.rationale = f"Score por reglas (sin IA): señales detectadas — {kws}."
    return t


def _call_claude(payload_items: list[dict]) -> list[dict]:
    body = {
        "model": CLAUDE_MODEL,
        "max_tokens": 4000,
        "system": SYSTEM,
        "messages": [{
            "role": "user",
            "content": "Evaluá estas licitaciones:\n" + json.dumps(
                payload_items, ensure_ascii=False, indent=1),
        }],
    }
    resp = requests.post(API_URL, timeout=120, json=body, headers={
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    })
    resp.raise_for_status()
    text = "".join(b.get("text", "") for b in resp.json().get("content", [])
                   if b.get("type") == "text")
    text = text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(text)


def score(candidates: list[Tender]) -> list[Tender]:
    top = candidates[:CLAUDE_TOP_N]
    rest = candidates[CLAUDE_TOP_N:]

    if DRY_RUN or not ANTHROPIC_API_KEY:
        log.warning("Scoring con Claude desactivado (dry-run o sin API key); fallback por reglas.")
        return sorted((_fallback(t) for t in candidates),
                      key=lambda t: t.probability, reverse=True)

    payload = [{
        "id": i,
        "titulo": t.title,
        "descripcion": t.description[:500],
        "organismo": t.agency,
        "jurisdiccion": t.jurisdiction,
        "fuente": t.source,
        "fecha_apertura": t.opening_date.isoformat() if t.opening_date else None,
        "presupuesto": t.budget,
    } for i, t in enumerate(top)]

    try:
        results = _call_claude(payload)
        by_id = {r["id"]: r for r in results if isinstance(r, dict) and "id" in r}
        for i, t in enumerate(top):
            r = by_id.get(i)
            if not r:
                _fallback(t)
                continue
            t.probability = max(0, min(100, int(r.get("probability", 0))))
            products = r.get("products") or t.products
            t.products = [p for p in products if isinstance(p, str)][:5]
            t.rationale = str(r.get("rationale", ""))[:400] or t.rationale
    except Exception as exc:  # noqa: BLE001
        log.error("Falló el scoring con Claude (%s); fallback por reglas.", exc)
        for t in top:
            _fallback(t)

    for t in rest:
        _fallback(t)
    return sorted(candidates, key=lambda t: t.probability, reverse=True)

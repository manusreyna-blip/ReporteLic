"""Fuente: CONTRAT.AR vía datos abiertos (datos.gob.ar, formato OCDS/CSV).

Obra pública: solo nos interesan procesos con componente tecnológico central
(datacenters, sistemas, conectividad); el filtro de keywords hace ese trabajo.
"""

from __future__ import annotations

import csv
import io
import logging

from .base import Tender, http_get, parse_date

log = logging.getLogger("radar.contratar")

CKAN_SEARCH = "https://datos.gob.ar/api/3/action/package_search"

COLS = {
    "title": ["nombre_procedimiento", "nombre_obra", "nombre", "objeto"],
    "description": ["descripcion", "descripción", "objeto"],
    "process_id": ["numero_procedimiento", "nro_procedimiento", "ocid"],
    "agency": ["reparticion", "repartición", "organismo", "jurisdiccion",
               "jurisdicción", "unidad_ejecutora"],
    "opening": ["fecha_apertura", "fecha_acto_apertura"],
    "status": ["estado_procedimiento", "estado"],
    "budget": ["monto_estimado", "presupuesto_oficial", "presupuesto"],
}


def _pick(row: dict, keys: list[str]) -> str:
    lowered = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
    for key in keys:
        if lowered.get(key):
            return lowered[key]
    return ""


def fetch() -> list[Tender]:
    tenders: list[Tender] = []
    try:
        data = http_get(CKAN_SEARCH, params={"q": "contratar obra pública", "rows": 8}).json()
    except Exception as exc:  # noqa: BLE001
        log.warning("CKAN search CONTRAT.AR falló: %s", exc)
        return tenders

    urls = []
    for pkg in data.get("result", {}).get("results", []):
        if "contratar" not in (pkg.get("title", "") + pkg.get("name", "")).lower():
            continue
        for res in pkg.get("resources", []):
            name = (res.get("name") or "").lower()
            if (res.get("format") or "").lower() == "csv" and \
               any(t in name for t in ("licitacion", "licitación", "procedimiento",
                                       "convocatoria", "proceso")):
                urls.append(res.get("url"))
    for url in urls[:2]:
        try:
            text = http_get(url, timeout=120).content.decode("utf-8-sig", errors="replace")
            delimiter = ";" if text[:4096].count(";") > text[:4096].count(",") else ","
            for row in csv.DictReader(io.StringIO(text), delimiter=delimiter):
                title = _pick(row, COLS["title"])
                if not title:
                    continue
                status = _pick(row, COLS["status"]).lower()
                if status and not any(s in status for s in
                                      ("publicad", "convocator", "abiert", "vigente")):
                    continue
                tenders.append(Tender(
                    title=title[:300],
                    description=_pick(row, COLS["description"])[:600],
                    process_id=_pick(row, COLS["process_id"]),
                    agency=_pick(row, COLS["agency"]) or "Obra pública nacional",
                    source="CONTRAT.AR",
                    jurisdiction="Nación",
                    opening_date=parse_date(_pick(row, COLS["opening"])),
                    budget=_pick(row, COLS["budget"]) or "N/D",
                    link="https://contratar.gob.ar",
                ))
        except Exception as exc:  # noqa: BLE001
            log.warning("Error con recurso CONTRAT.AR %s: %s", url, exc)
    log.info("CONTRAT.AR: %d filas crudas", len(tenders))
    return tenders

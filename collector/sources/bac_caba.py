"""Fuente: Buenos Aires Compras (BAC) vía datos abiertos del GCBA.

El GCBA publica los procesos de compra del sistema BAC en formato abierto
(OCDS / CSV) en data.buenosaires.gob.ar (CKAN).
"""

from __future__ import annotations

import csv
import io
import logging

from .base import Tender, http_get, parse_date

log = logging.getLogger("radar.bac")

CKAN_SEARCH = "https://data.buenosaires.gob.ar/api/3/action/package_search"
QUERIES = ["buenos aires compras", "compras y contrataciones bac"]

COL_CANDIDATES = {
    "title": ["nombre_proceso_compra", "nombre_proceso", "nombre", "objeto",
              "titulo", "título", "tender_title"],
    "description": ["descripcion", "descripción", "objeto", "tender_description"],
    "process_id": ["numero_proceso_compra", "numero_proceso", "nro_proceso",
                   "proceso_compra", "ocid", "tender_id"],
    "agency": ["reparticion", "repartición", "unidad_operativa_adquisiciones",
               "jurisdiccion", "jurisdicción", "buyer_name", "comprador"],
    "opening": ["fecha_apertura", "fecha_acto_apertura",
                "tender_tenderperiod_enddate", "fecha_fin_recepcion_ofertas"],
    "published": ["fecha_publicacion", "fecha_publicación", "tender_dateP"],
    "status": ["estado_proceso", "estado", "tender_status"],
    "budget": ["monto_estimado", "tender_value_amount", "presupuesto"],
}


def _pick(row: dict, keys: list[str]) -> str:
    lowered = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
    for key in keys:
        if lowered.get(key):
            return lowered[key]
    return ""


def _discover_resources() -> list[dict]:
    seen, resources = set(), []
    for q in QUERIES:
        try:
            data = http_get(CKAN_SEARCH, params={"q": q, "rows": 10}).json()
        except Exception as exc:  # noqa: BLE001
            log.warning("CKAN GCBA search falló para %r: %s", q, exc)
            continue
        for pkg in data.get("result", {}).get("results", []):
            if "compra" not in (pkg.get("title", "") + pkg.get("name", "")).lower():
                continue
            for res in pkg.get("resources", []):
                fmt = (res.get("format") or "").lower()
                name = (res.get("name") or "").lower()
                url = res.get("url") or ""
                if url in seen or fmt != "csv":
                    continue
                if any(t in name for t in ("proceso", "convocatoria", "licitacion",
                                           "licitación", "compra")):
                    seen.add(url)
                    resources.append({"name": name, "url": url,
                                      "modified": res.get("last_modified") or ""})
    resources.sort(key=lambda r: r["modified"], reverse=True)
    return resources[:3]


def fetch() -> list[Tender]:
    tenders: list[Tender] = []
    for res in _discover_resources():
        try:
            raw = http_get(res["url"], timeout=120).content
        except Exception as exc:  # noqa: BLE001
            log.warning("No se pudo descargar %s: %s", res["url"], exc)
            continue
        try:
            text = raw.decode("utf-8-sig", errors="replace")
            sample = text[:4096]
            delimiter = ";" if sample.count(";") > sample.count(",") else ","
            for row in csv.DictReader(io.StringIO(text), delimiter=delimiter):
                title = _pick(row, COL_CANDIDATES["title"])
                if not title:
                    continue
                status = _pick(row, COL_CANDIDATES["status"]).lower()
                if status and not any(s in status for s in
                                      ("publicad", "abiert", "convocator", "active",
                                       "vigente", "difusion", "difusión")):
                    continue
                pid = _pick(row, COL_CANDIDATES["process_id"])
                tenders.append(Tender(
                    title=title[:300],
                    description=_pick(row, COL_CANDIDATES["description"])[:600],
                    process_id=pid,
                    agency=_pick(row, COL_CANDIDATES["agency"]) or "GCBA",
                    source="BAC",
                    jurisdiction="CABA",
                    opening_date=parse_date(_pick(row, COL_CANDIDATES["opening"])),
                    budget=_pick(row, COL_CANDIDATES["budget"]) or "N/D",
                    link="https://www.buenosairescompras.gob.ar/" if not pid else
                         f"https://www.buenosairescompras.gob.ar/ (proceso {pid})",
                ))
        except Exception as exc:  # noqa: BLE001
            log.warning("Error parseando %s: %s", res["name"], exc)
    log.info("BAC: %d filas crudas", len(tenders))
    return tenders

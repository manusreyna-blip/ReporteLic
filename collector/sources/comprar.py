"""Fuente: COMPR.AR (Argentina Compra) vía datos abiertos oficiales (datos.gob.ar).

La ONC publica el dataset del sistema COMPR.AR en el Portal Nacional de Datos
Públicos (CKAN). Descubrimos los recursos dinámicamente con la API de CKAN para
no depender de URLs fijas que cambian de año a año.
"""

from __future__ import annotations

import csv
import io
import logging

from .base import Tender, http_get, parse_date

log = logging.getLogger("radar.comprar")

CKAN_SEARCH = "https://datos.gob.ar/api/3/action/package_search"
QUERIES = [
    "sistema de contrataciones electrónicas argentina compra",
    "comprar convocatorias",
]

# nombres de columna posibles (los CSVs de la ONC variaron a lo largo del tiempo)
COL_CANDIDATES = {
    "title": ["nombre_procedimiento", "procedimiento_nombre", "nombre_proceso",
              "convocatoria_nombre", "nombre", "objeto"],
    "description": ["descripcion", "descripción", "objeto_contratacion",
                    "objeto_contratación", "descripcion_procedimiento"],
    "process_id": ["numero_procedimiento", "procedimiento_numero", "numero_proceso",
                   "nro_procedimiento", "codigo_convocatoria"],
    "agency": ["unidad_operativa_contrataciones", "uoc", "reparticion", "repartición",
               "organismo", "servicio_administrativo_financiero", "unidad_ejecutora"],
    "opening": ["fecha_apertura", "fecha_acto_apertura", "apertura_fecha",
                "fecha_y_hora_apertura"],
    "published": ["fecha_publicacion", "fecha_publicación", "fecha_difusion"],
    "status": ["estado_procedimiento", "estado", "procedimiento_estado"],
    "link": ["url", "link", "enlace"],
    "budget": ["monto_estimado", "presupuesto", "importe"],
}


def _pick(row: dict, keys: list[str]) -> str:
    lowered = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
    for key in keys:
        if lowered.get(key):
            return lowered[key]
    return ""


def _discover_resources() -> list[dict]:
    """Busca en CKAN recursos CSV de convocatorias/procesos de COMPR.AR."""
    seen, resources = set(), []
    for q in QUERIES:
        try:
            data = http_get(CKAN_SEARCH, params={"q": q, "rows": 10}).json()
        except Exception as exc:  # noqa: BLE001
            log.warning("CKAN search falló para %r: %s", q, exc)
            continue
        for pkg in data.get("result", {}).get("results", []):
            blob = (pkg.get("title", "") + pkg.get("name", "")).lower()
            if "compra" not in blob and "contrat" not in blob:
                continue
            for res in pkg.get("resources", []):
                name = (res.get("name") or "").lower()
                fmt = (res.get("format") or "").lower()
                url = res.get("url") or ""
                if url in seen or fmt not in ("csv", "text/csv"):
                    continue
                if any(t in name for t in ("convocatoria", "proceso", "licitacion",
                                           "licitación", "procedimiento")):
                    seen.add(url)
                    resources.append({"name": name, "url": url,
                                      "modified": res.get("last_modified") or ""})
    # los modificados más recientemente primero
    resources.sort(key=lambda r: r["modified"], reverse=True)
    return resources[:4]


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
            reader = csv.DictReader(io.StringIO(text), delimiter=delimiter)
            for row in reader:
                title = _pick(row, COL_CANDIDATES["title"])
                if not title:
                    continue
                status = _pick(row, COL_CANDIDATES["status"]).lower()
                if status and not any(s in status for s in
                                      ("publicado", "convocator", "abierta", "vigente",
                                       "difusion", "difusión")):
                    continue
                opening = parse_date(_pick(row, COL_CANDIDATES["opening"]))
                pid = _pick(row, COL_CANDIDATES["process_id"])
                link = _pick(row, COL_CANDIDATES["link"]) or (
                    "https://comprar.gob.ar/BuscarAvanzado.aspx?qs=" + pid if pid
                    else "https://comprar.gob.ar")
                tenders.append(Tender(
                    title=title[:300],
                    description=_pick(row, COL_CANDIDATES["description"])[:600],
                    process_id=pid,
                    agency=_pick(row, COL_CANDIDATES["agency"]) or "Administración Pública Nacional",
                    source="COMPR.AR",
                    jurisdiction="Nación",
                    opening_date=opening,
                    budget=_pick(row, COL_CANDIDATES["budget"]) or "N/D",
                    link=link,
                ))
        except Exception as exc:  # noqa: BLE001
            log.warning("Error parseando %s: %s", res["name"], exc)
    log.info("COMPR.AR: %d filas crudas", len(tenders))
    return tenders

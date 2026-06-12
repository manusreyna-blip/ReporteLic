"""Fuente: Boletín Oficial de la Nación — Tercera Sección (Contrataciones).

Acá publican llamados los organismos descentralizados, universidades, fuerzas,
y empresas estatales que no siempre pasan por COMPR.AR. El sitio es público;
parseamos la sección del día y abrimos los avisos con rubro tecnológico.
"""

from __future__ import annotations

import logging
import re
import time

from bs4 import BeautifulSoup

from .base import Tender, http_get, parse_date
from ..config import MAX_DETAIL_FETCHES

log = logging.getLogger("radar.bo")

BASE = "https://www.boletinoficial.gob.ar"
SECTION_URL = f"{BASE}/seccion/tercera"

TECH_RUBRO_HINTS = (
    "soft", "proc. automatico de datos", "proc. automático de datos",
    "informatica", "informática", "computacion", "computación",
    "telecomunicacion", "telecomunicación", "servicios profesionales",
    "servicios tecnicos", "servicios técnicos",
)

APERTURA_RE = re.compile(
    r"(?:apertura|acto de apertura)[^\d]{0,120}?(\d{1,2}/\d{1,2}/\d{4})",
    re.IGNORECASE | re.DOTALL,
)
PROCESO_RE = re.compile(
    r"(?:proceso|licitaci[oó]n p[uú]blica|contrataci[oó]n)[\s:Nº°.]*"
    r"([A-Z0-9][\w./-]{2,40})", re.IGNORECASE)


def _detail(url: str) -> dict:
    soup = BeautifulSoup(http_get(url).text, "html.parser")
    body = soup.get_text(" ", strip=True)
    title_el = soup.find(["h1", "h2"])
    org = ""
    org_el = soup.find(string=re.compile(r"\S"))
    # el organismo suele venir en el primer encabezado fuerte de la página
    strong = soup.find("strong")
    if strong:
        org = strong.get_text(strip=True)
    apertura = None
    m = APERTURA_RE.search(body)
    if m:
        apertura = parse_date(m.group(1))
    pid = ""
    pm = PROCESO_RE.search(body)
    if pm:
        pid = pm.group(1).strip(" .,-")
    return {
        "title": (title_el.get_text(strip=True) if title_el else "")[:300],
        "agency": org[:200],
        "body": body[:1200],
        "opening": apertura,
        "process_id": pid,
    }


def fetch() -> list[Tender]:
    tenders: list[Tender] = []
    try:
        soup = BeautifulSoup(http_get(SECTION_URL).text, "html.parser")
    except Exception as exc:  # noqa: BLE001
        log.warning("No se pudo abrir la tercera sección: %s", exc)
        return tenders

    # links a avisos: /detalleAviso/tercera/<id>/<fecha>
    links = []
    for a in soup.select("a[href*='/detalleAviso/tercera/']"):
        href = a.get("href", "")
        context = a.get_text(" ", strip=True).lower()
        parent_text = a.find_parent().get_text(" ", strip=True).lower() if a.find_parent() else ""
        blob = context + " " + parent_text
        url = href if href.startswith("http") else BASE + href
        links.append((url, blob))

    seen = set()
    fetched = 0
    for url, blob in links:
        if url in seen:
            continue
        seen.add(url)
        # prioridad a rubros tech; si el rubro no es legible, igual abrimos
        # mientras quede presupuesto de requests
        is_tech_hint = any(h in blob for h in TECH_RUBRO_HINTS)
        if not is_tech_hint and fetched > MAX_DETAIL_FETCHES // 2:
            continue
        if fetched >= MAX_DETAIL_FETCHES:
            break
        try:
            d = _detail(url)
            fetched += 1
            time.sleep(0.4)  # respetar el sitio
        except Exception as exc:  # noqa: BLE001
            log.debug("Detalle falló %s: %s", url, exc)
            continue
        if not d["title"] and not d["body"]:
            continue
        tenders.append(Tender(
            title=d["title"] or d["body"][:140],
            description=d["body"],
            agency=d["agency"] or "Organismo nacional (ver aviso)",
            process_id=d["process_id"],
            source="BO-Nación",
            jurisdiction="Nación",
            opening_date=d["opening"],
            link=url,
        ))
    log.info("BO-Nación: %d avisos abiertos, %d candidatos", fetched, len(tenders))
    return tenders

"""Modelo de datos y utilidades compartidas por todas las fuentes."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta, timezone

import requests

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36 RadarLicitacionesAR/1.0"
)


def http_get(url: str, timeout: int = 45, **kwargs) -> requests.Response:
    headers = kwargs.pop("headers", {})
    headers.setdefault("User-Agent", USER_AGENT)
    headers.setdefault("Accept-Language", "es-AR,es;q=0.9")
    resp = requests.get(url, headers=headers, timeout=timeout, **kwargs)
    resp.raise_for_status()
    return resp


def today_art() -> date:
    """Fecha actual en horario argentino (UTC-3)."""
    return (datetime.now(timezone.utc) - timedelta(hours=3)).date()


def normalize(text: str) -> str:
    """minúsculas + sin tildes, para matching de keywords."""
    text = (text or "").lower()
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if unicodedata.category(c) != "Mn")


DATE_PATTERNS = [
    (re.compile(r"(\d{1,2})/(\d{1,2})/(\d{4})"), "dmy"),
    (re.compile(r"(\d{4})-(\d{1,2})-(\d{1,2})"), "ymd"),
]


def parse_date(raw: str) -> date | None:
    """Extrae la primera fecha reconocible de un string."""
    if not raw:
        return None
    raw = str(raw)
    for pattern, order in DATE_PATTERNS:
        m = pattern.search(raw)
        if m:
            try:
                if order == "dmy":
                    d, mth, y = (int(g) for g in m.groups())
                else:
                    y, mth, d = (int(g) for g in m.groups())
                return date(y, mth, d)
            except ValueError:
                continue
    return None


@dataclass
class Tender:
    title: str
    agency: str
    source: str                      # COMPR.AR | CONTRAT.AR | BAC | BO-Nación | ...
    link: str
    process_id: str = ""
    description: str = ""
    budget: str = "N/D"
    opening_date: date | None = None  # fecha de apertura de ofertas
    jurisdiction: str = ""            # Nación | CABA | PBA | provincia | municipio
    # campos calculados
    rule_score: int = 0
    probability: int = 0              # índice 0-100 de probabilidad de participación
    products: list[str] = field(default_factory=list)
    rationale: str = ""
    matched_keywords: list[str] = field(default_factory=list)

    @property
    def text_blob(self) -> str:
        return normalize(f"{self.title} {self.description} {self.agency}")

    def dedup_key(self) -> str:
        pid = normalize(self.process_id).replace(" ", "")
        if pid:
            return f"{self.source}|{pid}"
        return normalize(self.title)[:120]

    def to_dict(self) -> dict:
        d = asdict(self)
        d["opening_date"] = self.opening_date.isoformat() if self.opening_date else None
        d.pop("rule_score", None)
        d.pop("matched_keywords", None)
        return d

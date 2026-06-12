"""Genera latest.json, archivo histórico y cuerpo del email diario."""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from .sources.base import Tender, today_art

log = logging.getLogger("radar.report")

ROOT = Path(__file__).resolve().parent.parent

DIAS = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"]


def fecha_es(d: date) -> str:
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month - 1]} de {d.year}"


def _summary(tenders: list[Tender], sources_ok: list[str], sources_failed: list[str]) -> str:
    if not tenders:
        return ("Sin licitaciones tecnológicas activas detectadas hoy en las fuentes "
                f"disponibles ({', '.join(sources_ok) or 'ninguna'}).")
    hot = [t for t in tenders if t.probability >= 65]
    products: dict[str, int] = {}
    for t in tenders:
        for p in t.products:
            products[p] = products.get(p, 0) + 1
    top_products = ", ".join(p for p, _ in sorted(products.items(),
                                                  key=lambda kv: -kv[1])[:3]) or "N/D"
    urgent = sum(1 for t in tenders if t.opening_date and
                 (t.opening_date - today_art()).days <= 10)
    return (f"{len(tenders)} licitaciones tecnológicas activas detectadas, "
            f"{len(hot)} con probabilidad alta (≥65) y {urgent} con apertura en "
            f"menos de 10 días. Productos con más demanda: {top_products}.")


def build(tenders: list[Tender], stats: dict,
          sources_ok: list[str], sources_failed: list[str]) -> dict:
    today = today_art()
    report = {
        "date": fecha_es(today),
        "date_iso": today.isoformat(),
        "sources_checked": f"{len(sources_ok)} ok / {len(sources_failed)} con falla",
        "sources_ok": sources_ok,
        "sources_failed": sources_failed,
        "pipeline_stats": stats,
        "summary": _summary(tenders, sources_ok, sources_failed),
        "tenders": [t.to_dict() for t in tenders],
    }
    return report


def write(report: dict) -> None:
    payload = json.dumps(report, ensure_ascii=False, indent=2)
    (ROOT / "latest.json").write_text(payload, encoding="utf-8")
    archive = ROOT / "archive"
    archive.mkdir(exist_ok=True)
    (archive / f"{report['date_iso']}.json").write_text(payload, encoding="utf-8")
    docs = ROOT / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "latest.json").write_text(payload, encoding="utf-8")
    (docs / "email.html").write_text(email_html(report), encoding="utf-8")
    log.info("Reporte escrito: %d licitaciones", len(report["tenders"]))


def _prob_color(p: int) -> str:
    if p >= 65:
        return "#0E7A3D"
    if p >= 40:
        return "#B07000"
    return "#6B7280"


def email_html(report: dict) -> str:
    rows = []
    for t in report["tenders"][:10]:
        deadline = t.get("opening_date") or "N/D"
        rows.append(f"""
        <tr>
          <td style="padding:10px 12px;border-bottom:1px solid #E5E7EB;
                     font:700 18px/1 Arial;color:{_prob_color(t['probability'])};
                     text-align:center;">{t['probability']}</td>
          <td style="padding:10px 12px;border-bottom:1px solid #E5E7EB;
                     font:13px/1.45 Arial;color:#111827;">
            <strong>{t['title'][:140]}</strong><br>
            <span style="color:#4B5563;">{t['agency'][:110]} · {t['source']}</span><br>
            <span style="color:#1B5BFF;">{', '.join(t['products'][:4]) or '—'}</span>
          </td>
          <td style="padding:10px 12px;border-bottom:1px solid #E5E7EB;
                     font:12px/1.3 Arial;color:#111827;white-space:nowrap;">
            {deadline}</td>
        </tr>""")
    rows_html = "".join(rows) or (
        '<tr><td colspan="3" style="padding:16px;font:13px Arial;color:#6B7280;">'
        'Sin licitaciones tecnológicas activas hoy.</td></tr>')
    return f"""<!doctype html><html><body style="margin:0;background:#F3F4F6;padding:24px;">
<table width="640" align="center" cellpadding="0" cellspacing="0"
       style="background:#fff;border-radius:8px;overflow:hidden;">
  <tr><td style="background:#10243E;padding:18px 24px;">
    <span style="font:700 16px Arial;color:#fff;">Radar de Licitaciones Tech — Argentina</span><br>
    <span style="font:12px Arial;color:#9DB4D0;">{report['date']}</span>
  </td></tr>
  <tr><td style="padding:18px 24px;font:13px/1.5 Arial;color:#111827;">
    {report['summary']}<br>
    <span style="color:#6B7280;font-size:12px;">Fuentes: {report['sources_checked']}
    {('· Fallaron: ' + ', '.join(report['sources_failed'])) if report['sources_failed'] else ''}</span>
  </td></tr>
  <tr><td style="padding:0 24px 8px;">
    <table width="100%" cellpadding="0" cellspacing="0">
      <tr>
        <th style="font:700 11px Arial;color:#6B7280;text-align:center;padding:6px 12px;">PROB.</th>
        <th style="font:700 11px Arial;color:#6B7280;text-align:left;padding:6px 12px;">LICITACIÓN</th>
        <th style="font:700 11px Arial;color:#6B7280;text-align:left;padding:6px 12px;">APERTURA</th>
      </tr>
      {rows_html}
    </table>
  </td></tr>
  <tr><td style="padding:14px 24px 22px;font:12px Arial;">
    <a href="__PAGE_URL__" style="color:#1B5BFF;">Ver reporte completo →</a>
  </td></tr>
</table></body></html>"""

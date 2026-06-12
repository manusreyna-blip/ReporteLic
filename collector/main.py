"""Orquestador del radar: recolecta -> filtra -> scorea -> reporta."""

from __future__ import annotations

import logging
import sys

from . import filters, report, scoring
from .sources import bac_caba, boletin_oficial, comprar, contratar

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("radar")

SOURCES = {
    "COMPR.AR": comprar.fetch,
    "CONTRAT.AR": contratar.fetch,
    "BAC": bac_caba.fetch,
    "BO-Nación": boletin_oficial.fetch,
}


def run(source_overrides: dict | None = None) -> dict:
    sources = source_overrides or SOURCES
    all_tenders, ok, failed = [], [], []
    for name, fetcher in sources.items():
        try:
            items = fetcher()
            all_tenders.extend(items)
            ok.append(name)
            log.info("%s: %d items", name, len(items))
        except Exception as exc:  # noqa: BLE001
            failed.append(name)
            log.error("Fuente %s falló: %s", name, exc)

    candidates, stats = filters.run_pipeline(all_tenders)
    scored = scoring.score(candidates)
    result = report.build(scored, stats, ok, failed)
    report.write(result)
    return result


if __name__ == "__main__":
    r = run()
    print(f"\n{r['summary']}")
    sys.exit(0)

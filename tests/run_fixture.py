"""Prueba end-to-end del pipeline con datos de fixture (sin red, sin API).

Uso:  RADAR_DRY_RUN=1 python -m tests.run_fixture
"""

from datetime import timedelta

from collector import main
from collector.sources.base import Tender, today_art

T = today_art()


def fake_source():
    return [
        # alta relevancia, activa
        Tender(title="Servicio de implementación de plataforma CRM omnicanal para atención ciudadana",
               description="Plataforma cloud de gestión de casos, integración WhatsApp, "
                           "asistente virtual con inteligencia artificial y tableros de control.",
               agency="PAMI - INSSJP", source="COMPR.AR", jurisdiction="Nación",
               process_id="80-0099-LPU26", opening_date=T + timedelta(days=12),
               link="https://comprar.gob.ar/proceso/80-0099-LPU26"),
        # media, activa, urgente
        Tender(title="Desarrollo y mantenimiento de software del sistema de turnos",
               description="Fábrica de software, metodología ágil, interoperabilidad con sistemas legacy vía API.",
               agency="Ministerio de Salud - GCBA", source="BAC", jurisdiction="CABA",
               process_id="401-0123-LPU26", opening_date=T + timedelta(days=5),
               link="https://www.buenosairescompras.gob.ar/"),
        # baja señal tech, activa
        Tender(title="Adquisición de licencias de software antivirus",
               description="Suscripción de software de seguridad endpoint por 24 meses.",
               agency="ARCA", source="BO-Nación", jurisdiction="Nación",
               opening_date=T + timedelta(days=20), link="https://example.gob.ar/1"),
        # excluida por rubro
        Tender(title="Provisión de medicamentos oncológicos",
               description="Logística y dispensa de medicamentos.", agency="PAMI",
               source="COMPR.AR", jurisdiction="Nación",
               opening_date=T + timedelta(days=9), link="https://example.gob.ar/2"),
        # vencida (no activa)
        Tender(title="Plataforma de gobierno digital provincial",
               description="Transformación digital, expediente electrónico, nube.",
               agency="Gobierno de Mendoza", source="COMPR.AR", jurisdiction="Mendoza",
               opening_date=T - timedelta(days=3), link="https://example.gob.ar/3"),
        # duplicada
        Tender(title="Servicio de implementación de plataforma CRM omnicanal para atención ciudadana",
               description="dup", agency="PAMI - INSSJP", source="COMPR.AR",
               process_id="80-0099-LPU26", opening_date=T + timedelta(days=12),
               link="https://comprar.gob.ar/proceso/80-0099-LPU26"),
        # sin fecha (no activa)
        Tender(title="Sistema informático de gestión documental",
               description="Digitalización de expedientes.", agency="Municipio X",
               source="BO-Nación", opening_date=None, link="https://example.gob.ar/4"),
    ]


if __name__ == "__main__":
    result = main.run(source_overrides={"FIXTURE": fake_source})
    tenders = result["tenders"]
    assert result["sources_ok"] == ["FIXTURE"], result["sources_ok"]
    assert len(tenders) == 3, f"esperaba 3, hubo {len(tenders)}: {[t['title'] for t in tenders]}"
    titles = [t["title"] for t in tenders]
    assert "CRM omnicanal" in titles[0], "el CRM de PAMI debería rankear primero"
    assert all(t["probability"] > 0 for t in tenders)
    assert any("Service Cloud" in t["products"] for t in tenders)
    assert all(t["opening_date"] > T.isoformat() for t in tenders)
    print("\nOK ✔ pipeline:", result["pipeline_stats"])
    for t in tenders:
        print(f"  [{t['probability']:>3}] {t['title'][:70]} | {t['products']}")

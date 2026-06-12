# Radar de Licitaciones Tech — Salesforce Argentina

Agente automático que corre **todos los días (lunes a sábado, 07:30 ART)** y:

1. Recolecta licitaciones públicas de fuentes oficiales de datos abiertos: **COMPR.AR** y **CONTRAT.AR** (datos.gob.ar), **BAC/GCBA** (data.buenosaires.gob.ar) y el **Boletín Oficial de la Nación** (tercera sección: organismos descentralizados, universidades, empresas estatales).
2. Filtra solo procesos **activos** (fecha de apertura posterior a hoy) con señal tecnológica.
3. Calcula un **índice de probabilidad de participación de Salesforce (0-100)** — las reglas filtran, **Claude** scorea las mejores candidatas vía API.
4. Mapea los **productos Salesforce aplicables** (Service Cloud, Agentforce, MuleSoft, Tableau, Data Cloud, etc.).
5. Publica `latest.json` + histórico en `archive/`, actualiza la **página web** (GitHub Pages) y envía un **email diario** con el top.

## Puesta en marcha (una sola vez, ~10 minutos)

### 1. Crear el repositorio
1. En github.com → **New repository** → nombre `sf-arg-tenders` → **Public** → Create.
2. Subí todo el contenido de este paquete: **Add file → Upload files** → arrastrá las carpetas y archivos → Commit.
   (O por consola: `git init && git add . && git commit -m "radar v1" && git push`.)

### 2. Configurar los secrets
En el repo → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Valor |
|---|---|
| `ANTHROPIC_API_KEY` | Tu API key de console.anthropic.com (scoring con Claude) |
| `MAIL_USERNAME` | Tu Gmail/Workspace que envía (ej: el de ElectroMov) |
| `MAIL_PASSWORD` | **App password** de Google (myaccount.google.com → Seguridad → Verificación en 2 pasos → Contraseñas de aplicaciones) — no tu contraseña normal |
| `MAIL_TO` | Email donde querés recibir el reporte |

> Sin `ANTHROPIC_API_KEY` el radar igual corre con scoring por reglas (menos preciso). Sin los secrets de mail, simplemente no envía email (el paso está marcado como no bloqueante).

### 3. Activar GitHub Pages
**Settings → Pages → Source: Deploy from a branch → Branch: `main` / carpeta `/docs`** → Save.
La página queda en `https://TU_USUARIO.github.io/sf-arg-tenders/`.

### 4. Primera corrida (prueba)
**Actions → radar-diario → Run workflow**. En ~3-5 minutos vas a tener `latest.json` actualizado, la página con datos y el email en tu casilla. Después corre solo cada día.

## Para Cowork / otros agentes
URL estable del reporte: `https://raw.githubusercontent.com/TU_USUARIO/sf-arg-tenders/main/latest.json`

## Estructura
```
collector/            código del agente
  config.py           keywords, pesos, productos, cuentas prioritarias  ← acá se tunea
  sources/            COMPR.AR, CONTRAT.AR, BAC, Boletín Oficial
  filters.py          vigencia + relevancia + pre-score
  scoring.py          índice de probabilidad con Claude (híbrido)
  report.py           latest.json, archivo, email
docs/                 página web (GitHub Pages) + copia del JSON
archive/              histórico diario
tests/run_fixture.py  prueba local sin red: RADAR_DRY_RUN=1 python -m tests.run_fixture
```

## Cobertura y límites conocidos (v1)
- **Cubre:** Nación (COMPR.AR + CONTRAT.AR + Boletín Oficial, que incluye empresas estatales y descentralizados) y CABA (BAC).
- **No cubre todavía:** PBAC y portales provinciales sin datos abiertos, y municipios (publican fragmentado). Para exhaustividad municipal, el camino es sumar un agregador con API (ej. licit.ar) como fuente adicional en `collector/sources/`.
- Los datasets abiertos se actualizan con frecuencia variable según el organismo; el campo `sources_failed` del reporte avisa si una fuente no respondió.
- La primera corrida real va a revelar los nombres exactos de columnas de los CSV oficiales; los parsers ya contemplan las variantes históricas, pero si una fuente devuelve 0 resultados, revisá el log del workflow.

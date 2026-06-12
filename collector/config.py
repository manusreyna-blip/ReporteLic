"""Configuración central del Radar de Licitaciones Tech — Salesforce Argentina."""

import os

# ── Ejecución ────────────────────────────────────────────────────────────────
TIMEZONE_OFFSET_HOURS = -3  # ART (UTC-3)
MAX_DETAIL_FETCHES = 60     # tope de fichas de detalle por fuente
CLAUDE_TOP_N = 25           # cuántas candidatas se mandan a Claude para scoring fino
CLAUDE_MODEL = os.environ.get("RADAR_CLAUDE_MODEL", "claude-sonnet-4-6")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
DRY_RUN = os.environ.get("RADAR_DRY_RUN", "") == "1"  # sin llamadas a Claude

# ── Keywords de inclusión (señal tech) ──────────────────────────────────────
# término -> peso para el pre-score por reglas (0-10)
INCLUDE_KEYWORDS = {
    # CRM / atención ciudadana — núcleo Salesforce
    "crm": 10, "salesforce": 10,
    "atencion ciudadana": 9, "atención ciudadana": 9, "servicio al ciudadano": 9,
    "contact center": 9, "centro de contacto": 9, "call center": 8,
    "omnicanal": 9, "mesa de ayuda": 8, "help desk": 8,
    "asistente virtual": 9, "chatbot": 9, "agente de ia": 9, "agentes de ia": 9,
    "whatsapp": 8, "gestion de casos": 8, "gestión de casos": 8,
    "gestion de turnos": 7, "gestión de turnos": 7,
    # Plataforma / cloud
    "saas": 7, "nube": 6, "cloud": 6, "plataforma digital": 7,
    "low-code": 7, "low code": 7, "no-code": 6,
    "transformacion digital": 6, "transformación digital": 6,
    "gobierno digital": 6, "digitalizacion": 5, "digitalización": 5,
    "expediente electronico": 5, "expediente electrónico": 5,
    # Integración / datos
    "interoperabilidad": 7, "integracion de sistemas": 7, "integración de sistemas": 7,
    "api": 5, "middleware": 6, "esb": 6, "mulesoft": 10,
    "data lake": 6, "lago de datos": 6, "gestion de datos": 5, "gestión de datos": 5,
    "cdp": 7, "vision 360": 8, "visión 360": 8,
    # Analytics
    "business intelligence": 7, "tableau": 10, "analytics": 6,
    "tablero de control": 6, "dashboard": 6, "visualizacion de datos": 6,
    "visualización de datos": 6,
    # Automatización / desarrollo
    "automatizacion": 5, "automatización": 5, "workflow": 5, "bpm": 6,
    "gestion de procesos": 5, "gestión de procesos": 5,
    "desarrollo de software": 5, "mantenimiento de software": 5,
    "fabrica de software": 5, "fábrica de software": 5,
    "sistema informatico": 4, "sistema informático": 4, "software": 4,
    "aplicacion movil": 5, "aplicación móvil": 5, "aplicativo": 4,
    # Field service / marketing
    "ordenes de trabajo": 5, "órdenes de trabajo": 5, "servicio de campo": 6,
    "field service": 7, "fleet management": 5,
    "marketing digital": 5, "comunicacion ciudadana": 6, "comunicación ciudadana": 6,
    "email marketing": 6, "envio de sms": 5, "envío de sms": 5,
    # Genéricas débiles
    "licencias de software": 4, "suscripcion de software": 4, "suscripción de software": 4,
    "tecnologia de la informacion": 3, "tecnología de la información": 3,
    "informatica": 3, "informática": 3, "plataforma": 3, "portal web": 4,
    "sitio web": 3, "inteligencia artificial": 6,
}

# ── Keywords de exclusión (descarta si dominan el objeto) ───────────────────
EXCLUDE_KEYWORDS = [
    "obra civil", "construccion", "construcción", "pavimento", "asfalto",
    "bacheo", "cordon cuneta", "cordón cuneta", "alimentos", "alimentario",
    "medicamento", "oncologic", "oncológic", "hemodialisis", "hemodiálisis",
    "insumos medicos", "insumos médicos", "hospitalario", "quirurgic", "quirúrgic",
    "limpieza", "residuos", "recoleccion de residuos", "recolección de residuos",
    "vigilancia", "seguridad fisica", "seguridad física", "uniformes",
    "vehiculos", "vehículos", "camioneta", "ambulancia", "combustible",
    "mobiliario", "luminaria", "iluminacion", "iluminación", "ascensor",
    "impresion de", "impresión de", "papel", "toner", "tóner",
    "catering", "viandas", "protesis", "prótesis", "ortesis", "órtesis",
    "equipamiento de red", "insumos de red", "cableado", "ups", "grupo electrogeno",
    "grupo electrógeno", "aire acondicionado",
]

# ── Mapeo keyword -> productos Salesforce ───────────────────────────────────
PRODUCT_MAP = {
    "Service Cloud": [
        "atencion ciudadana", "atención ciudadana", "servicio al ciudadano",
        "contact center", "centro de contacto", "call center", "omnicanal",
        "mesa de ayuda", "help desk", "gestion de casos", "gestión de casos",
        "whatsapp", "gestion de turnos", "gestión de turnos",
    ],
    "Agentforce": [
        "asistente virtual", "chatbot", "agente de ia", "agentes de ia",
        "inteligencia artificial", "whatsapp",
    ],
    "Sales Cloud": ["crm", "gestion comercial", "gestión comercial", "pipeline"],
    "Marketing Cloud": [
        "marketing digital", "comunicacion ciudadana", "comunicación ciudadana",
        "email marketing", "envio de sms", "envío de sms", "campañas",
    ],
    "MuleSoft": [
        "interoperabilidad", "integracion de sistemas", "integración de sistemas",
        "api", "middleware", "esb", "mulesoft",
    ],
    "Tableau": [
        "business intelligence", "tableau", "analytics", "tablero de control",
        "dashboard", "visualizacion de datos", "visualización de datos",
    ],
    "Data Cloud": [
        "data lake", "lago de datos", "cdp", "vision 360", "visión 360",
        "gestion de datos", "gestión de datos",
    ],
    "Field Service": [
        "ordenes de trabajo", "órdenes de trabajo", "servicio de campo",
        "field service", "fleet management",
    ],
    "Salesforce Platform": [
        "low-code", "low code", "no-code", "desarrollo de software",
        "mantenimiento de software", "fabrica de software", "fábrica de software",
        "bpm", "workflow", "automatizacion", "automatización", "aplicativo",
        "aplicacion movil", "aplicación móvil", "expediente electronico",
        "expediente electrónico", "plataforma digital",
    ],
}

# ── Cuentas prioritarias (boost en el pre-score) ────────────────────────────
PRIORITY_AGENCIES = {
    "pami": 3, "inssjp": 3, "anses": 3, "arca": 3, "afip": 3, "renaper": 3,
    "ypf": 2, "aerolineas": 2, "aerolíneas": 2, "bcra": 2, "banco central": 2,
    "banco nacion": 2, "banco nación": 2, "arsat": 2, "enacom": 2,
    "oficina nacional de contrataciones": 2, "jefatura de gabinete": 1,
    "ciudad inteligente": 2, "dgsaciu": 3, "mendoza": 1, "cordoba": 1, "córdoba": 1,
    "epec": 2, "santa fe": 1,
}

# Pre-score mínimo para pasar a la etapa de scoring con Claude
RULE_SCORE_THRESHOLD = 4

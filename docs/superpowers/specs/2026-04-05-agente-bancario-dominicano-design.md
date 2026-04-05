# Agente Bancario Dominicano — Spec de Diseño
**Fecha:** 2026-04-05
**Estado:** Aprobado por usuario
**Stack:** 100% herramientas gratuitas / open-source

---

## 1. Objetivo

Construir un agente que recopile datos del sistema bancario dominicano y macroeconómicos, los analice, y genere tres tipos de entregables listos para publicar en LinkedIn (perfil personal) o compartir en reuniones de board. El usuario revisa y aprueba cada draft antes de la publicación final.

**Audiencia del contenido:** analistas financieros, banqueros, reguladores, board members — posicionamiento institucional/técnico.

---

## 2. Arquitectura General

```
python run.py [flash|mensual|board]
        │
        ▼
ORCHESTRATOR AGENT (Claude Agent SDK · claude-sonnet-4-6)
        │
        ├── DATA MCP SERVER (Python local, mcp SDK)
        │       ├── get_bcrd_indicators
        │       ├── get_sb_banking_data
        │       ├── get_hacienda_fiscal
        │       ├── get_imf_data
        │       └── get_worldbank_data
        │
        ├── FINANCIAL PLUGINS (financial-services-plugins repo)
        │       ├── sector-overview (adaptado RD)
        │       ├── competitive-analysis (entidades bancarias)
        │       ├── earnings-analysis (resultados bancarios)
        │       └── comps-analysis (benchmarking regional)
        │
        └── SUB-AGENTS
                ├── Post Agent      → outputs/posts/YYYY-MM-DD-{tipo}.md
                ├── Board Agent     → outputs/reports/YYYY-MM-DD-board.pdf
                ├── Carousel Agent  → outputs/carousel/YYYY-MM-DD-carousel.pptx
                └── Format Decision Agent → recomienda carousel vs. texto
```

**Loop de revisión:** después de generar drafts, el agente los presenta al usuario. El usuario da instrucciones adicionales en lenguaje natural. El agente refina todos los outputs afectados y re-presenta. Se repite hasta que el usuario escribe "aprobado".

---

## 3. Capa de Datos — MCP Server

### 3.1 Fuentes y herramientas

| Herramienta | Fuente | Método | Frecuencia |
|---|---|---|---|
| `get_bcrd_indicators` | apibcrd.bancentral.gov.do | REST (libre) | Diario |
| `get_sb_banking_data` | superbancos.gob.do | Web scraping | Mensual |
| `get_hacienda_fiscal` | hacienda.gob.do | Web scraping | Mensual |
| `get_imf_data` | data.imf.org | REST (libre, sin API key) | Trimestral |
| `get_worldbank_data` | api.worldbank.org | REST (libre, sin API key) | Anual/trimestral |

### 3.2 Indicadores BCRD (get_bcrd_indicators)

**Tasas de interés — por tipo de entidad:**
- Bancos Múltiples: tasa activa ponderada, tasa pasiva ponderada
- Asociaciones de Ahorro y Préstamos (AAyP): tasa activa, tasa pasiva
- Bancos de Ahorro y Crédito: tasa activa, tasa pasiva
- Tasa interbancaria (overnight)
- Tasa de Política Monetaria (TPM)

**Actividad económica:**
- IMAE — variación mensual e interanual
- Inflación — acumulada, interanual, por componentes (alimentos, transporte, vivienda)
- Tipo de cambio compra/venta, variación interanual

**Comportamiento del cliente bancario:**
- Certificados de Depósito: variación interanual (correlación con tasa pasiva)
- Captaciones por instrumento: CDs, cuentas de ahorro, cuentas corrientes
- Crédito privado por sector: consumo, comercial, hipotecario, microcrédito
- Spread activo-pasivo por tipo de entidad

### 3.3 Indicadores Superintendencia de Bancos (get_sb_banking_data)

**Sistema agregado:**
- Solvencia: IAC (Índice de Adecuación de Capital), cobertura de cartera vencida
- Rentabilidad: ROE, ROA, margen de intermediación, utilidades netas
- Cartera: total, por sector, vencida (NPL), tasa de morosidad
- Captaciones totales, por instrumento

**Por entidad (ranking):**
- Top 5 mayor crecimiento interanual de cartera de crédito (monto + %)
- Top 5 mayor deterioro de cartera — variación NPL interanual en pp
- Datos individuales de todos los bancos múltiples y AAyP

### 3.4 Caché local

Cada llamada guarda resultado en `data/cache/YYYY-MM-DD/{fuente}.json`. Si el archivo existe y es del día actual, no se vuelve a hacer la solicitud. Permite trabajo offline y evita sobrecarga a las fuentes.

---

## 4. Financial Plugins (adaptaciones)

Los siguientes skills del repo `financial-services-plugins` se adaptan al contexto dominicano:

| Plugin original | Adaptación |
|---|---|
| `sector-overview` | Panorama del sistema bancario dominicano por subsector |
| `competitive-analysis` | Análisis comparativo entre entidades financieras RD |
| `earnings-analysis` | Análisis de resultados trimestrales/anuales de la banca |
| `comps-analysis` | Benchmarking RD vs. Centroamérica y Caribe (vía IMF FSI) |

---

## 5. Sub-Agentes y Outputs

### 5.1 Post Agent

**Modo flash (semanal/reactivo)** — se dispara ante dato relevante nuevo:
```
📊 [Indicador] | [Fecha]

[1-2 oraciones: dato + variación vs. período anterior]
[1 oración: implicación para clientes/sistema bancario]

[Fuente] · #BancaDominicana #BCRD #SistemaFinanciero
```

**Modo mensual (profundo):**
```
🏦 Barómetro Bancario Dominicano | [Mes Año]

ENTORNO MACRO
· TPM: X% | Inflación: X% i.a. | IMAE: +X% | USD/DOP: X

SISTEMA BANCARIO
· Crédito privado: +X% i.a. | Captaciones: +X%
· Spread activo-pasivo BM: X pp | AAyP: X pp

TOP ENTIDADES (variación interanual)
Cartera de crédito:
  🥇 [Banco X]: +XX% | 🥈 [Banco Y]: +XX% | 🥉 [Banco Z]: +XX%
Morosidad (NPL):
  ⚠️ [Banco A]: +X.Xpp | [Banco B]: +X.Xpp | [Banco C]: +X.Xpp

QUÉ DICE EL COMPORTAMIENTO DEL CLIENTE
[Narrativa: ej. "La subida de tasa pasiva a 6.8%
 impulsó un crecimiento de 12% en CDs en BM..."]

PERSPECTIVA
[1 párrafo: qué vigilar el próximo mes]

Fuente: BCRD · SB · [Fecha]
#BancaDominicana #FinanzasDominicanas #BCRD #Macroeconomía
```

**Output:** `outputs/posts/YYYY-MM-DD-{flash|mensual}.md`

### 5.2 Board Agent — Reporte ejecutivo PDF

Estructura (8-10 páginas, estilo consultoría):

| Sección | Contenido |
|---|---|
| Portada | Título · período · fecha |
| Resumen ejecutivo | 5 KPIs headline con semáforo verde/amarillo/rojo |
| Entorno macro | TPM · inflación · IMAE · tipo de cambio · serie histórica 12m |
| Sistema bancario | Solvencia (IAC, NPL, cobertura) · Rentabilidad (ROE, ROA, margen) · Crecimiento (crédito, captaciones) |
| Ranking de entidades | Top 5 mayor crecimiento de cartera i.a. · Top 5 mayor deterioro NPL · Bubble chart: crecimiento vs. morosidad (tamaño = cartera) |
| Comportamiento del cliente | CDs vs. tasa pasiva · Composición crédito por sector · Waterfall |
| Contexto regional | IMF FSI: RD vs. Centroamérica y Caribe · WorldBank: crédito/PIB |
| Contexto fiscal | Hacienda: deuda/PIB · ejecución presupuestaria · impacto en liquidez |
| Perspectivas | Riesgos · oportunidades · indicadores a vigilar |
| Apéndice | Tablas de datos completos · metodología · fuentes |

**Tecnología:** `matplotlib` + `plotly` → `weasyprint` para PDF.
**Paleta:** azul corporativo / gris oscuro / semáforo verde-amarillo-rojo.
**Output:** `outputs/reports/YYYY-MM-DD-board.pdf`

### 5.3 Carousel Agent — Slides LinkedIn

Formato: 1080×1080px (cuadrado). 8-10 slides. Tecnología: `python-pptx`.

| Slide | Contenido |
|---|---|
| 1 | Portada: título impactante + fecha |
| 2 | 5 KPIs en cards visuales (más relevantes del mes) |
| 3 | Macro: tipo de cambio · inflación · IMAE · TPM (barras) |
| 4 | Tasas activas vs. pasivas BM y AAyP — evolución (línea) |
| 5 | Crédito por segmento: consumo / comercial / hipotecario (dona o barras apiladas) |
| 6 | Captaciones: narrativa visual "Cuando la tasa sube → los CDs crecen" |
| 7A | "¿Quién creció más?" — Top 3 por cartera (barras horizontales) |
| 7B | "¿Quién tiene más morosidad?" — Top 3 NPL (semáforo + delta i.a.) |
| 8 | Contexto regional: RD vs. región IMF FSI (comparativa horizontal) |
| 9 | Perspectivas: 3 bullets visuales — qué vigilar el próximo mes |
| 10 | CTA + Firma: "¿Qué indicador te interesa profundizar?" + nombre/perfil |

**Output:** `outputs/carousel/YYYY-MM-DD-carousel.pptx` + `.pdf`

### 5.4 Format Decision Agent

Evalúa ambos outputs (post + carousel) y recomienda cuál publicar basado en:

| Criterio | Carousel | Post texto |
|---|---|---|
| 3+ indicadores con variación notable este mes | ✅ | |
| Dato puntual urgente/reactivo | | ✅ |
| Hay tendencia visual clara que narrar | ✅ | |
| Flash semanal | | ✅ |
| Análisis mensual completo | ✅ | |

Produce recomendación con justificación antes del draft review loop.

---

## 6. Draft Review Loop

```
[Agente genera drafts]
        │
        ▼
Presenta al usuario:
  · Resumen de datos clave recopilados
  · Post draft (completo)
  · Board report: secciones headline + KPIs
  · Carousel: outline de slides con datos
  · Recomendación: carousel vs. texto + justificación
        │
        ▼
Usuario da instrucciones en lenguaje natural:
  "hazlo más técnico"
  "agrega comparación con el mes pasado"
  "el slide 7A necesita incluir BanReservas"
  "cambia el tono del board report a más formal"
        │
        ▼
Agente refina todos los outputs afectados
        │
        ▼
Repite hasta que usuario escribe "aprobado"
        │
        ▼
Genera archivos finales en outputs/
```

---

## 7. Estructura de Directorios

```
MissionControl/
├── financial-services-plugins/     ← repo clonado
├── agent/
│   ├── run.py                      ← punto de entrada
│   ├── orchestrator.py             ← agente principal
│   ├── mcp_server.py               ← servidor MCP local
│   ├── sub_agents/
│   │   ├── post_agent.py
│   │   ├── board_agent.py
│   │   ├── carousel_agent.py
│   │   └── format_decision_agent.py
│   ├── data_sources/
│   │   ├── bcrd.py
│   │   ├── superbancos.py
│   │   ├── hacienda.py
│   │   ├── imf.py
│   │   └── worldbank.py
│   ├── templates/
│   │   ├── carousel_base.pptx      ← template reutilizable
│   │   └── board_report_base.html  ← template HTML → PDF
│   └── skills/                     ← adaptaciones de financial-plugins
│       ├── sector_overview_rd.md
│       ├── competitive_analysis_rd.md
│       └── earnings_analysis_rd.md
├── data/
│   └── cache/                      ← JSON por fecha y fuente
└── outputs/
    ├── posts/
    ├── reports/
    └── carousel/
```

---

## 8. Stack Tecnológico (100% gratuito)

| Componente | Herramienta |
|---|---|
| Agente principal | `anthropic` Python SDK (Claude Agent SDK) |
| MCP server | `mcp` Python SDK |
| Scraping | `requests` + `beautifulsoup4` |
| Gráficas | `matplotlib` + `plotly` |
| PDF | `weasyprint` |
| PPTX | `python-pptx` |
| IMF data | data.imf.org REST API (sin API key) |
| World Bank | api.worldbank.org REST API (sin API key) |
| BCRD | apibcrd.bancentral.gov.do (libre) |
| SB / Hacienda | Web scraping |

---

## 9. Modos de Ejecución

```bash
python run.py flash      # Flash semanal — dato puntual
python run.py mensual    # Análisis mensual completo + board + carousel
python run.py board      # Solo board report (sin post LinkedIn)
python run.py carousel   # Solo carousel (sobre análisis existente)
```

---

## 10. Fuentes de Datos y Disclaimer

Todas las fuentes son públicas e institucionales:
- **BCRD** — Banco Central de la República Dominicana
- **SB** — Superintendencia de Bancos de la República Dominicana
- **Hacienda** — Ministerio de Hacienda de la República Dominicana
- **IMF** — Financial Soundness Indicators (FSI), libre acceso
- **World Bank** — Open Data API, libre acceso

Los posts incluirán atribución a fuentes y fecha de los datos.

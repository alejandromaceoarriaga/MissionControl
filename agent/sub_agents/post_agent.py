# agent/sub_agents/post_agent.py
import json
import anthropic

FLASH_PROMPT = """Eres un analista financiero dominicano de alto nivel escribiendo para LinkedIn.

Genera un post corto (máx 150 palabras) sobre este indicador bancario dominicano:

Indicador: {indicator}
Datos: {data}

Formato EXACTO:
📊 [Indicador] | [Fecha]

[1-2 oraciones: valor actual + variación vs período anterior]
[1 oración: implicación para clientes o sistema bancario dominicano]

Fuente: BCRD · #BancaDominicana #BCRD #SistemaFinanciero

Sé técnico, preciso y conciso. Solo devuelve el texto del post."""

MENSUAL_PROMPT = """Eres un analista financiero dominicano senior escribiendo el reporte mensual para LinkedIn.

Genera el "Barómetro Bancario Dominicano" basado en estos datos:
{data}

Formato EXACTO:
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
[2-3 oraciones con insight basado en datos]

PERSPECTIVA
[1 párrafo: máx 3 puntos clave a vigilar el próximo mes]

Fuente: BCRD · SB · [Fecha]
#BancaDominicana #FinanzasDominicanas #BCRD #Macroeconomía

Solo devuelve el texto del post."""

REFINE_PROMPT = """Tienes este borrador de post de LinkedIn sobre banca dominicana:

{draft}

El usuario solicita: {instruction}

Datos disponibles: {data}

Aplica los cambios manteniendo el formato y calidad técnica. Solo devuelve el post revisado."""


class PostAgent:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        self.client = anthropic.Anthropic()
        self.model = model

    def _call_claude(self, prompt: str) -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    def generate_flash(self, data: dict, indicator: str = "tpm") -> str:
        prompt = FLASH_PROMPT.format(
            indicator=indicator,
            data=json.dumps(data.get("bcrd", {}), ensure_ascii=False, indent=2),
        )
        return self._call_claude(prompt)

    def generate_mensual(self, data: dict) -> str:
        prompt = MENSUAL_PROMPT.format(
            data=json.dumps(data, ensure_ascii=False, indent=2)[:4000],
        )
        return self._call_claude(prompt)

    def refine(self, draft: str, instruction: str, data: dict) -> str:
        prompt = REFINE_PROMPT.format(
            draft=draft,
            instruction=instruction,
            data=json.dumps(data, ensure_ascii=False, indent=2)[:3000],
        )
        return self._call_claude(prompt)

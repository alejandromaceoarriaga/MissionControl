# agent/sub_agents/board_agent.py
import json
import os
from datetime import date
from io import BytesIO

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.backends.backend_pdf import PdfPages
import anthropic

# Color palette
DARK_BLUE = '#1a1a2e'
MED_BLUE = '#3182ce'
LIGHT_BLUE = '#63b3ed'
GREEN = '#38a169'
YELLOW = '#d69e2e'
RED = '#e53e3e'
GRAY = '#718096'
LIGHT_GRAY = '#f7fafc'


class BoardAgent:
    def __init__(self, output_dir: str = "outputs/reports"):
        self.output_dir = output_dir
        self.client = anthropic.Anthropic()
        os.makedirs(output_dir, exist_ok=True)

    def _build_kpi_summary(self, data: dict) -> dict:
        bcrd = data.get("bcrd", {})
        tasas = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        activa = tasas.get("activa") or 0
        pasiva = tasas.get("pasiva") or 0
        spread = round(activa - pasiva, 2)
        imae_val = bcrd.get("imae", {}).get("var_interanual") or 0
        inf_val = bcrd.get("inflacion", {}).get("var_interanual") or 0
        tpm_val = bcrd.get("tpm", {}).get("value") or 0
        return {
            "tpm": {"value": tpm_val, "delta": "Tasa Política Monetaria", "color": "green"},
            "imae": {"value": imae_val, "delta": "IMAE var. i.a.", "color": "green" if imae_val > 3 else "yellow" if imae_val > 0 else "red"},
            "inflacion": {"value": inf_val, "delta": "Inflación i.a.", "color": "green" if inf_val < 5 else "yellow" if inf_val < 8 else "red"},
            "spread_bm": {"value": spread, "delta": "Spread Bancos Múltiples", "color": "green" if spread < 8 else "yellow"},
            "reservas": {"value": bcrd.get("reservas", {}).get("brutas_mm_usd") or 0, "delta": "Reservas brutas (US$MM)", "color": "green"},
            "tipo_cambio": {"value": bcrd.get("tipo_cambio", {}).get("venta") or 0, "delta": "USD/DOP venta", "color": "green"},
        }

    def _color_map(self, color_name: str) -> str:
        return {"green": GREEN, "yellow": YELLOW, "red": RED}.get(color_name, GRAY)

    def _page_cover(self, pdf: PdfPages, period: str):
        fig, ax = plt.subplots(figsize=(11, 8.5))
        fig.patch.set_facecolor(DARK_BLUE)
        ax.set_facecolor(DARK_BLUE)
        ax.axis('off')
        ax.text(0.5, 0.75, 'SISTEMA BANCARIO DOMINICANO', transform=ax.transAxes,
                fontsize=14, color=MED_BLUE, ha='center', fontweight='bold')
        ax.text(0.5, 0.60, 'Barómetro Ejecutivo', transform=ax.transAxes,
                fontsize=32, color='white', ha='center', fontweight='bold')
        ax.text(0.5, 0.48, period, transform=ax.transAxes,
                fontsize=20, color=LIGHT_BLUE, ha='center')
        ax.text(0.5, 0.35, f'Generado: {date.today()}', transform=ax.transAxes,
                fontsize=12, color=GRAY, ha='center')
        ax.text(0.5, 0.10, 'Fuente: BCRD · Superintendencia de Bancos · IMF · World Bank · Hacienda',
                transform=ax.transAxes, fontsize=9, color=GRAY, ha='center')
        plt.tight_layout()
        pdf.savefig(fig, facecolor=DARK_BLUE)
        plt.close(fig)

    def _page_kpis(self, pdf: PdfPages, kpis: dict):
        fig, ax = plt.subplots(figsize=(11, 8.5))
        ax.set_facecolor('white')
        ax.axis('off')
        ax.text(0.5, 0.96, 'RESUMEN EJECUTIVO — KPIs CLAVE', transform=ax.transAxes,
                fontsize=16, color=DARK_BLUE, ha='center', fontweight='bold')
        ax.plot([0.05, 0.95], [0.93, 0.93], color=MED_BLUE, linewidth=2, transform=ax.transAxes, clip_on=False)
        items = list(kpis.items())
        cols, rows = 3, 2
        for i, (key, kpi) in enumerate(items[:6]):
            col, row = i % cols, i // cols
            x = 0.05 + col * 0.33
            y = 0.75 - row * 0.38
            w, h = 0.28, 0.32
            rect = mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01",
                                            facecolor=LIGHT_GRAY, edgecolor=self._color_map(kpi['color']),
                                            linewidth=3, transform=ax.transAxes, clip_on=False)
            ax.add_patch(rect)
            ax.text(x + w/2, y + h - 0.04, kpi['delta'], transform=ax.transAxes,
                    fontsize=8, color=GRAY, ha='center', fontweight='bold')
            ax.text(x + w/2, y + h/2, f"{kpi['value']}", transform=ax.transAxes,
                    fontsize=22, color=DARK_BLUE, ha='center', fontweight='bold')
            dot_color = self._color_map(kpi['color'])
            circle = plt.Circle((x + 0.03, y + h - 0.035), 0.008, color=dot_color, transform=ax.transAxes)
            ax.add_patch(circle)
        pdf.savefig(fig)
        plt.close(fig)

    def _page_macro_chart(self, pdf: PdfPages, data: dict, period: str):
        bcrd = data.get("bcrd", {})
        tasas = bcrd.get("tasas_bancarias", {}).get("bancos_multiples", {})
        labels = ['TPM', 'Activa BM', 'Pasiva BM', 'IMAE i.a.', 'Inflación i.a.']
        values = [
            bcrd.get("tpm", {}).get("value") or 0,
            tasas.get("activa") or 0,
            tasas.get("pasiva") or 0,
            bcrd.get("imae", {}).get("var_interanual") or 0,
            bcrd.get("inflacion", {}).get("var_interanual") or 0,
        ]
        colors = [DARK_BLUE, MED_BLUE, LIGHT_BLUE, GREEN, YELLOW]
        fig, axes = plt.subplots(1, 2, figsize=(11, 7))
        fig.suptitle(f'ENTORNO MACROECONÓMICO — {period}', fontsize=14, color=DARK_BLUE, fontweight='bold', y=0.98)

        # Bar chart
        ax = axes[0]
        bars = ax.bar(labels, values, color=colors, edgecolor='white', linewidth=0.5, width=0.6)
        for bar, val in zip(bars, values):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.08,
                    f'{val:.2f}%', ha='center', va='bottom', fontsize=9, fontweight='bold', color=DARK_BLUE)
        ax.set_ylabel('Porcentaje (%)', color=GRAY)
        ax.set_title('Indicadores de Tasas', color=DARK_BLUE, fontweight='bold')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.set_facecolor(LIGHT_GRAY)
        ax.tick_params(axis='x', labelsize=8)

        # Table
        ax2 = axes[1]
        ax2.axis('off')
        table_data = [
            ['Indicador', 'Valor', 'Período'],
            ['TPM', f"{bcrd.get('tpm',{}).get('value','N/D')}%", bcrd.get('tpm',{}).get('date','')],
            ['Activa BM', f"{tasas.get('activa','N/D')}%", bcrd.get('tasas_bancarias',{}).get('date','')],
            ['Pasiva BM', f"{tasas.get('pasiva','N/D')}%", ''],
            ['AAyP Activa', f"{bcrd.get('tasas_bancarias',{}).get('aayp',{}).get('activa','N/D')}%", ''],
            ['Interbancaria', f"{bcrd.get('tasas_bancarias',{}).get('interbancaria','N/D')}%", ''],
            ['IMAE i.a.', f"+{bcrd.get('imae',{}).get('var_interanual','N/D')}%", bcrd.get('imae',{}).get('date','')],
            ['Inflación i.a.', f"{bcrd.get('inflacion',{}).get('var_interanual','N/D')}%", bcrd.get('inflacion',{}).get('date','')],
            ['USD/DOP venta', f"RD${bcrd.get('tipo_cambio',{}).get('venta','N/D')}", bcrd.get('tipo_cambio',{}).get('date','')],
            ['Reservas brutas', f"US${bcrd.get('reservas',{}).get('brutas_mm_usd','N/D')}MM", bcrd.get('reservas',{}).get('date','')],
        ]
        table = ax2.table(cellText=table_data[1:], colLabels=table_data[0],
                          cellLoc='left', loc='center', bbox=[0, 0, 1, 1])
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor(DARK_BLUE)
                cell.set_text_props(color='white', fontweight='bold')
            elif row % 2 == 0:
                cell.set_facecolor(LIGHT_GRAY)
            cell.set_edgecolor('white')
        ax2.set_title('Datos Detallados', color=DARK_BLUE, fontweight='bold')
        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    def _page_rankings(self, pdf: PdfPages, data: dict):
        rankings = data.get("sb", {}).get("rankings", {})
        top_cartera = rankings.get("top_cartera_growth", [])
        top_npl = rankings.get("top_npl_increase", [])

        fig, axes = plt.subplots(1, 2, figsize=(11, 7))
        fig.suptitle('RANKING DE ENTIDADES BANCARIAS', fontsize=14, color=DARK_BLUE, fontweight='bold', y=0.98)

        # Top cartera
        ax1 = axes[0]
        if top_cartera:
            names = [e.get("entidad", f"E{i+1}") for i, e in enumerate(top_cartera[:5])]
            values = [e.get("_growth_pct", 0) for e in top_cartera[:5]]
            colors_bar = [MED_BLUE, LIGHT_BLUE, '#90cdf4', '#bee3f8', '#ebf8ff']
            bars = ax1.barh(names[::-1], values[::-1], color=colors_bar[:len(names)], edgecolor='white')
            for bar, val in zip(bars, values[::-1]):
                ax1.text(val + 0.2, bar.get_y() + bar.get_height()/2,
                         f'+{val:.1f}%', va='center', fontsize=9, fontweight='bold', color=DARK_BLUE)
            ax1.set_xlabel('Crecimiento i.a. (%)', color=GRAY)
            ax1.spines['top'].set_visible(False)
            ax1.spines['right'].set_visible(False)
            ax1.set_facecolor(LIGHT_GRAY)
        ax1.set_title('Top Crecimiento de Cartera (i.a.)', color=DARK_BLUE, fontweight='bold')

        # Bubble chart: crecimiento vs morosidad
        ax2 = axes[1]
        if top_cartera:
            npl_lookup = {e.get("entidad", ""): e.get("_growth_pct", 0) for e in top_npl}
            cart_names = [e.get("entidad", f"E{i+1}") for i, e in enumerate(top_cartera[:6])]
            cart_vals = [e.get("_growth_pct", 0) for e in top_cartera[:6]]
            npl_vals = [npl_lookup.get(n, 0) for n in cart_names]
            sizes = [200 + abs(v) * 40 for v in cart_vals]
            scatter = ax2.scatter(cart_vals, npl_vals, s=sizes, c=range(len(cart_vals)),
                                   cmap='Blues', alpha=0.7, edgecolors=DARK_BLUE, linewidth=1)
            for i, name in enumerate(cart_names):
                ax2.annotate(name, (cart_vals[i], npl_vals[i]),
                             textcoords="offset points", xytext=(0, 8), ha='center', fontsize=7)
            ax2.axhline(y=0, color=GRAY, linestyle='--', linewidth=0.8, alpha=0.5)
            ax2.axvline(x=0, color=GRAY, linestyle='--', linewidth=0.8, alpha=0.5)
            ax2.set_xlabel('Crecimiento Cartera i.a. (%)', color=GRAY)
            ax2.set_ylabel('Delta Morosidad (pp)', color=GRAY)
            ax2.set_facecolor(LIGHT_GRAY)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
        ax2.set_title('Crecimiento vs. Morosidad\n(tamano = cartera relativa)', color=DARK_BLUE, fontweight='bold')

        plt.tight_layout()
        pdf.savefig(fig)
        plt.close(fig)

    def _page_regional(self, pdf: PdfPages, data: dict):
        imf_data = data.get("imf", {})
        wb_data = data.get("wb", {})
        hacienda = data.get("hacienda", {}).get("fiscal", {})

        fig, ax = plt.subplots(figsize=(11, 7))
        ax.axis('off')
        fig.suptitle('CONTEXTO REGIONAL E INTERNACIONAL', fontsize=14, color=DARK_BLUE, fontweight='bold', y=0.98)

        table_data = [
            ['Indicador', 'Valor', 'Fuente', 'Período'],
            ['Crédito Privado / PIB', f"{wb_data.get('credit_gdp', [{}])[0].get('value', 'N/D') if wb_data.get('credit_gdp') else 'N/D'}%", 'World Bank', wb_data.get('credit_gdp', [{}])[0].get('year', '') if wb_data.get('credit_gdp') else ''],
            ['Capital Adequacy (IAC)', f"{imf_data.get('capital_adequacy', {}).get('value', 'N/D')}%", 'IMF FSI', imf_data.get('capital_adequacy', {}).get('year', '')],
            ['NPL Ratio', f"{imf_data.get('npl_ratio', {}).get('value', 'N/D')}%", 'IMF FSI', imf_data.get('npl_ratio', {}).get('year', '')],
            ['ROE (Sistema)', f"{imf_data.get('roe', {}).get('value', 'N/D')}%", 'IMF FSI', imf_data.get('roe', {}).get('year', '')],
            ['Deuda Pública / PIB', f"{hacienda.get('deuda_pib_pct', 'N/D')}%", 'Hacienda', hacienda.get('date', '')],
        ]
        table = ax.table(cellText=table_data[1:], colLabels=table_data[0],
                         cellLoc='center', loc='center', bbox=[0.02, 0.1, 0.96, 0.8])
        table.auto_set_font_size(False)
        table.set_fontsize(11)
        for (row, col), cell in table.get_celld().items():
            if row == 0:
                cell.set_facecolor(DARK_BLUE)
                cell.set_text_props(color='white', fontweight='bold')
            elif row % 2 == 0:
                cell.set_facecolor(LIGHT_GRAY)
            cell.set_edgecolor('white')
            cell.set_height(0.12)
        pdf.savefig(fig)
        plt.close(fig)

    def _page_perspectivas(self, pdf: PdfPages, perspectivas: str):
        fig, ax = plt.subplots(figsize=(11, 7))
        fig.patch.set_facecolor(DARK_BLUE)
        ax.set_facecolor(DARK_BLUE)
        ax.axis('off')
        ax.text(0.5, 0.92, 'PERSPECTIVAS Y RIESGOS', transform=ax.transAxes,
                fontsize=16, color='white', ha='center', fontweight='bold')
        ax.text(0.5, 0.85, '-' * 60, transform=ax.transAxes, fontsize=10, color=MED_BLUE, ha='center')
        # Wrap the perspectivas text
        lines = perspectivas.strip().split('\n')
        y_pos = 0.75
        for line in lines[:15]:
            ax.text(0.08, y_pos, line[:100], transform=ax.transAxes,
                    fontsize=10, color='white', va='top', wrap=True)
            y_pos -= 0.055
            if y_pos < 0.05:
                break
        ax.text(0.5, 0.03, 'Fuente: BCRD · SB · IMF · World Bank · Hacienda',
                transform=ax.transAxes, fontsize=8, color=GRAY, ha='center')
        pdf.savefig(fig, facecolor=DARK_BLUE)
        plt.close(fig)

    def _get_perspectivas(self, data: dict, period: str) -> str:
        prompt = f"""Como analista financiero senior del sistema bancario dominicano, basándote en estos datos para {period}:

TPM: {data.get('bcrd', {}).get('tpm', {}).get('value', 'N/D')}%
IMAE i.a.: {data.get('bcrd', {}).get('imae', {}).get('var_interanual', 'N/D')}%
Inflación i.a.: {data.get('bcrd', {}).get('inflacion', {}).get('var_interanual', 'N/D')}%
Spread BM: {round((data.get('bcrd', {}).get('tasas_bancarias', {}).get('bancos_multiples', {}).get('activa') or 0) - (data.get('bcrd', {}).get('tasas_bancarias', {}).get('bancos_multiples', {}).get('pasiva') or 0), 2)} pp

Escribe 5-7 bullets concisos de perspectivas y riesgos para el próximo período.
Formato: bullet con emoji (riesgo, oportunidad, vigilar).
Max 120 palabras total."""
        msg = self.client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text

    def generate(self, data: dict, period: str = None) -> str:
        if not period:
            period = date.today().strftime("%B %Y")
        kpis = self._build_kpi_summary(data)
        perspectivas = self._get_perspectivas(data, period)

        filename = f"{date.today()}-board-report.pdf"
        output_path = os.path.join(self.output_dir, filename)

        with PdfPages(output_path) as pdf:
            self._page_cover(pdf, period)
            self._page_kpis(pdf, kpis)
            self._page_macro_chart(pdf, data, period)
            self._page_rankings(pdf, data)
            self._page_regional(pdf, data)
            self._page_perspectivas(pdf, perspectivas)

        return output_path

# agent/orchestrator.py
import os
from datetime import date

from agent.data_sources.bcrd import BCRDClient
from agent.data_sources.superbancos import SuperbancosClient
from agent.data_sources.imf import IMFClient
from agent.data_sources.worldbank import WorldBankClient
from agent.data_sources.hacienda import HaciendaClient
from agent.sub_agents.post_agent import PostAgent
from agent.sub_agents.board_agent import BoardAgent
from agent.sub_agents.carousel_agent import CarouselAgent
from agent.sub_agents.format_decision_agent import FormatDecisionAgent


class Orchestrator:
    def __init__(self, mode: str, output_dir: str = "outputs"):
        self.mode = mode  # "flash" | "mensual"
        self.output_dir = output_dir
        self._data: dict = {}
        self._drafts: dict = {}

        # Sub-agents
        self.post_agent = PostAgent()
        self.board_agent = BoardAgent(output_dir=os.path.join(output_dir, "reports"))
        self.carousel_agent = CarouselAgent(output_dir=os.path.join(output_dir, "carousel"))
        self.format_agent = FormatDecisionAgent()

        # Data clients
        self.bcrd = BCRDClient()
        self.sb = SuperbancosClient()
        self.imf = IMFClient()
        self.wb = WorldBankClient()
        self.hacienda = HaciendaClient()

    def fetch_data(self) -> dict:
        """Fetch all data sources and store on instance."""
        print("Fetching data from all sources...")

        bcrd_data = self.bcrd.get_all()
        print("  [OK] BCRD")

        try:
            sb_data = self.sb.get_banking_data()
            print("  [OK] Superintendencia de Bancos")
        except Exception as e:
            print(f"  [WARN] SB failed: {e}")
            sb_data = {}

        try:
            imf_data = self.imf.get_capital_adequacy()
            print("  [OK] IMF")
        except Exception as e:
            print(f"  [WARN] IMF failed: {e}")
            imf_data = {}

        try:
            wb_data = self.wb.get_credit_to_gdp()
            print("  [OK] World Bank")
        except Exception as e:
            print(f"  [WARN] World Bank failed: {e}")
            wb_data = []

        try:
            hacienda_data = self.hacienda.get_fiscal_data()
            print("  [OK] Hacienda")
        except Exception as e:
            print(f"  [WARN] Hacienda failed: {e}")
            hacienda_data = {}

        self._data = {
            "bcrd": bcrd_data,
            "sb": sb_data,
            "imf": imf_data,
            "worldbank": wb_data,
            "hacienda": hacienda_data,
        }
        return self._data

    def generate_drafts(self) -> dict:
        """Generate all output drafts based on mode."""
        data = self._data
        summary = self.format_agent.summarize_data(data)
        fmt = self.format_agent.decide(self.mode, summary)

        drafts: dict = {"format_recommendation": fmt}

        if self.mode == "flash":
            print("Generating flash post...")
            drafts["post"] = self.post_agent.generate_flash(data)
        else:
            print("Generating mensual post...")
            drafts["post"] = self.post_agent.generate_mensual(data)
            print("Generating board PDF report...")
            drafts["board_path"] = self.board_agent.generate(data)
            print("Generating LinkedIn carousel PPTX...")
            drafts["carousel_path"] = self.carousel_agent.generate(data)

        self._drafts = drafts
        return drafts

    def refine(self, instructions: str) -> dict:
        """Refine the post draft with user instructions."""
        current_post = self._drafts.get("post", "")
        data_json = str(self._data)[:2000]  # truncate for prompt
        refined = self.post_agent.refine(current_post, instructions, data_json)
        self._drafts["post"] = refined
        return self._drafts

    def save_finals(self) -> dict:
        """Save final approved outputs to disk."""
        today = date.today().strftime("%Y-%m-%d")
        posts_dir = os.path.join(self.output_dir, "posts")
        os.makedirs(posts_dir, exist_ok=True)

        post_path = os.path.join(posts_dir, f"{today}-post.md")
        with open(post_path, "w", encoding="utf-8") as f:
            f.write(self._drafts.get("post", ""))

        paths = {"post_path": post_path}

        if "board_path" in self._drafts:
            paths["board_path"] = self._drafts["board_path"]

        if "carousel_path" in self._drafts:
            paths["carousel_path"] = self._drafts["carousel_path"]

        return paths

    def present_drafts(self) -> None:
        """Print all current drafts to stdout for human review."""
        fmt = self._drafts.get("format_recommendation", {})
        print("\n" + "=" * 70)
        print(f"RECOMENDACION DE FORMATO: {fmt.get('recommendation', '?').upper()}")
        print(f"Razon: {fmt.get('reason', '')}")
        print("=" * 70)

        print("\n--- POST LINKEDIN ---")
        print(self._drafts.get("post", "(no generado)"))

        if "board_path" in self._drafts:
            print(f"\n--- BOARD REPORT PDF ---")
            print(f"Archivo: {self._drafts['board_path']}")

        if "carousel_path" in self._drafts:
            print(f"\n--- CAROUSEL PPTX ---")
            print(f"Archivo: {self._drafts['carousel_path']}")

        print("\n" + "=" * 70)

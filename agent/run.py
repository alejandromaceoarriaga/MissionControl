#!/usr/bin/env python3
# agent/run.py — CLI entry point for Agente Bancario Dominicano
"""
Usage:
    python agent/run.py flash       # Quick flash post on a single indicator
    python agent/run.py mensual     # Full monthly Barómetro + board PDF + carousel
"""
import sys
from agent.orchestrator import Orchestrator

HELP = """
Agente Bancario Dominicano
==========================
Uso:
  python agent/run.py flash     → Post flash (indicador puntual)
  python agent/run.py mensual   → Barometro mensual completo + PDF + PPTX

En el review loop:
  - Escribe instrucciones para refinar el borrador
  - Escribe 'aprobado' para guardar y salir
  - Escribe 'salir' para cancelar sin guardar
"""


def review_loop(orch: Orchestrator) -> None:
    """Interactive human-in-the-loop review until user types 'aprobado'."""
    orch.present_drafts()

    while True:
        print("\nRevision > ", end="", flush=True)
        try:
            user_input = input().strip()
        except (EOFError, KeyboardInterrupt):
            print("\nCancelado.")
            sys.exit(0)

        if not user_input:
            continue

        if user_input.lower() == "aprobado":
            paths = orch.save_finals()
            print("\n Outputs guardados:")
            for key, path in paths.items():
                print(f"  {key}: {path}")
            print("\nPost listo para publicar en LinkedIn.")
            break

        if user_input.lower() in ("salir", "exit", "cancel"):
            print("Saliendo sin guardar.")
            sys.exit(0)

        # Treat anything else as refinement instructions
        print("\nRefinando...")
        orch.refine(user_input)
        orch.present_drafts()


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(HELP)
        sys.exit(0)

    mode = sys.argv[1].lower()
    if mode not in ("flash", "mensual"):
        print(f"Error: modo '{mode}' no reconocido. Usa 'flash' o 'mensual'.")
        sys.exit(1)

    print(f"\nIniciando Agente Bancario Dominicano — modo: {mode.upper()}")
    orch = Orchestrator(mode=mode)

    orch.fetch_data()
    orch.generate_drafts()
    review_loop(orch)


if __name__ == "__main__":
    main()

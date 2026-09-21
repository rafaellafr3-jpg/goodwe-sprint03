"""
main.py
Interface de linha de comando para conversar com o agente GoodWe.

Uso:
    python -m app.main
    python -m app.main --model anthropic_claude
"""

import argparse
import uuid

from app.agent import GoodWeAgent
from app.config import MODEL_CONFIGS, DEFAULT_MODEL_KEY


def main():
    parser = argparse.ArgumentParser(description="Chat com o agente GoodWe (Sprint 03)")
    parser.add_argument(
        "--model",
        choices=list(MODEL_CONFIGS.keys()),
        default=DEFAULT_MODEL_KEY,
        help="Qual modelo/config usar (ver app/config.py)",
    )
    parser.add_argument(
        "--session",
        default=None,
        help="ID de sessão fixo (para retomar uma conversa). Se omitido, gera um novo.",
    )
    args = parser.parse_args()

    session_id = args.session or str(uuid.uuid4())
    agent = GoodWeAgent(model_key=args.model)

    print(f"[GoodWe Agent] modelo={args.model} sessão={session_id}")
    print("Digite 'sair' para encerrar.\n")

    while True:
        user_input = input("Você: ").strip()
        if user_input.lower() in {"sair", "exit", "quit"}:
            break
        response = agent.send(session_id, user_input)
        print(f"GoodWe Agent: {response}\n")


if __name__ == "__main__":
    main()

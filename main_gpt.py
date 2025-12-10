import os
import argparse
from dotenv import load_dotenv
from openai import OpenAI
import random
from datetime import datetime
from solverz3 import *
from save_results import *
import time
import io
import sys


# ============================================================
# 1. ORIGINAL SOLVER (KEPT UNCHANGED)
# ============================================================

def solver(puzzle_arg=None):
    # CLI args em linha com main.py
    parser = argparse.ArgumentParser(description="Resolve puzzles de cavaleiros e patifes")
    parser.add_argument("--puzzle", "-p", help="Nome do arquivo .txt em puzzles/ a ser usado (ex: puzzle1.txt)")
    args = parser.parse_args()

    # Load environment
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")

    if api_key:
        print("Chave de API carregada com sucesso (OpenAI)")
    else:
        print("OPENAI_API_KEY não encontrada no arquivo .env.")
        return

    client = OpenAI(api_key=api_key)
    model_name = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

    puzzles_dir = "puzzles"

    # Puzzle via argumento (aceita com/sem .txt e caminho absoluto)
    if args.puzzle:
        puzzle_arg = args.puzzle if args.puzzle.endswith(".txt") else f"{args.puzzle}.txt"

        if os.path.isabs(puzzle_arg):
            caminho_puzzle = puzzle_arg
        else:
            caminho_puzzle = os.path.join(puzzles_dir, puzzle_arg)

        if not os.path.exists(caminho_puzzle):
            print(f"Puzzle '{puzzle_arg}' não encontrado!")
            return

        arquivo_escolhido = os.path.basename(caminho_puzzle)
    else:
        arquivos = sorted([f for f in os.listdir(puzzles_dir) if f.endswith(".txt")])
        if not arquivos:
            print("Nenhum arquivo .txt encontrado na pasta 'puzzles'.")
            return
        arquivo_escolhido = arquivos[0]
        caminho_puzzle = os.path.join(puzzles_dir, arquivo_escolhido)

    # Lista arquivos para fallback aleatório (mantém compatibilidade com main.py)
    arquivos = [f for f in os.listdir(puzzles_dir) if f.endswith(".txt")]
    if not arquivos:
        print("Nenhum arquivo .txt encontrado na pasta 'puzzles'.")
        return

    if args.puzzle:
        puzzle_nome = args.puzzle if args.puzzle.endswith(".txt") else f"{args.puzzle}.txt"
        if puzzle_nome not in arquivos and not os.path.isabs(puzzle_nome):
            print(f"Arquivo {args.puzzle} não encontrado na pasta 'puzzles'.")
            return
        arquivo_escolhido = puzzle_nome
    else:
        arquivo_escolhido = random.choice(arquivos)
    caminho_puzzle = caminho_puzzle if args.puzzle and os.path.isabs(puzzle_arg) else os.path.join(puzzles_dir, arquivo_escolhido)

    # Read puzzle file
    with open(caminho_puzzle, "r", encoding="utf-8") as f:
        puzzle = f.read().strip()

    def ask_gpt(prompt: str) -> str:
        """Dispara um chat.completions.create e devolve apenas o texto da primeira escolha."""
        resp = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        return resp.choices[0].message.content

    # ======= LLM (SEM Z3) =======
    resposta = ask_gpt(
        puzzle + ". Diretamente resolva o problema: Quem podemos garantir (Ou quem é consequência lógica) que é cavaleiro e quem é patife?"
        " Responda de forma direta, poucas linhas, exemplo: A: Cavaleiro\n B: Patife\n C: Indeterminado\nNão é necessário exibir a cadeia de pensamento, sempre em ordem alfabética,"
        " para problemas impossíveis, retorne: Inconsistente para todas as pessoas"
    )

    print(puzzle)
    print("\nSEM Z3")
    print(resposta)

    # ======= LLM (COM Z3) =======
    resposta_direta = ask_gpt(
        puzzle + " Agora com ajuda da biblioteca Z3, traduza o problema para Z3 e resolva (Não é necessário envio do código): "
        "Quem podemos garantir que é cavaleiro e quem é patife? Responda de forma direta, poucas linhas, apenas informando o que é "
        "garantido ou não exemplo: A: Cavaleiro\n B: Patife\n C: Indeterminado\n"
        "Não é necessário exibir a cadeia de pensamento, sempre em ordem alfabética, para problemas impossíveis, retorne: Inconsistente para todas as pessoas"
    )

    print("\nCOM Z3")
    print(resposta_direta)

    # ======= Z3 (REAL) =======
    try:
        variables, restrictions = parse_puzzle_to_z3(puzzle)
        resultado_z3 = generic_solver(variables, restrictions)

        print("\nZ3: Consequências Lógicas (O que é garantido)")
        consequencias = logical_consequences(variables, restrictions)

        for nome, status in consequencias.items():
            print(f"{nome}: {status}")

        # Compare WITHOUT Z3 (registro principal)
        match_sem = compare_results(resposta, consequencias)
        salva_comparacao(
            arquivo_escolhido,
            puzzle,
            resposta,
            consequencias,
            match_sem,
            results_path="resultados/results_gpt.jsonl",
            comparacoes_path="resultados/comparacoes_gpt.txt",
        )

        if match_sem:
            print("\nLLM ACERTOU O PUZZLE SEM Z3")
        else:
            print("\nLLM ERROU O PUZZLE SEM Z3")

        # Compare WITH Z3 (apenas exibição; não salva em results_gpt.jsonl para evitar duplicatas)
        match_com = compare_results(resposta_direta, consequencias)
        if match_com:
            print("\nLLM ACERTOU O PUZZLE COM Z3")
        else:
            print("\nLLM ERROU O PUZZLE COM Z3")

    except Exception as e:
        print(f"Erro ao resolver com Z3: {e}")



# ============================================================
# 2. STREAMING WRAPPER (SAFE, NON-DESTRUCTIVE)
# ============================================================

def solve(puzzle_arg=None):
    """
    Wrapper que captura todos os prints do solver() e envia via yield
    para o frontend web como streaming.
    NÃO altera nenhuma lógica original.
    """
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer

    # Executa o solver original normalmente
    try:
        if puzzle_arg:
            solver(puzzle_arg)
        else:
            solver()
    except Exception as e:
        yield f"Erro: {e}"

    # Restaura saída padrão
    sys.stdout = old_stdout

    # Envia linha a linha
    output = buffer.getvalue().splitlines()
    for line in output:
        yield line



# ============================================================
# 3. TERMINAL MODE (UNCHANGED)
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--puzzle", help="Nome do puzzle")
    args = parser.parse_args()

    if args.puzzle:
        solver(args.puzzle)
    else:
        solver()

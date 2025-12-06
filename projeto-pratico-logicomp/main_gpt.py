import os
import argparse
from dotenv import load_dotenv
import google.generativeai as genai
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

    # CLI args
    parser = argparse.ArgumentParser(description="Resolve puzzles com Gemini + Z3")
    parser.add_argument("--puzzle", help="Nome do arquivo .txt em puzzles/ a ser usado")
    args = parser.parse_args()

    # Load environment
    load_dotenv()
    api_key = os.getenv("API_KEY")

    if not api_key:
        print("Chave de API não encontrada no arquivo .env.")
        return
    
    print("Chave de API carregada com sucesso")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-pro")

    puzzles_dir = "puzzles"

    # Puzzle via argumento
    if args.puzzle:
        puzzle_arg = args.puzzle if args.puzzle.endswith(".txt") else f"{args.puzzle}.txt"
        caminho_puzzle = os.path.join(puzzles_dir, puzzle_arg)

        if not os.path.exists(caminho_puzzle):
            print(f"Puzzle '{puzzle_arg}' não encontrado!")
            return

        arquivo_escolhido = os.path.basename(caminho_puzzle)

    else:
        arquivos = [f for f in os.listdir(puzzles_dir) if f.endswith(".txt")]
        if not arquivos:
            print("Nenhum arquivo .txt encontrado na pasta 'puzzles'.")
            return

        arquivo_escolhido = random.choice(arquivos)
        caminho_puzzle = os.path.join(puzzles_dir, arquivo_escolhido)

    # Read puzzle file
    with open(caminho_puzzle, "r", encoding="utf-8") as f:
        puzzle = f.read().strip()

    print(puzzle)
    print("\nSEM Z3")

    # LLM (SEM Z3)
    resposta = model.generate_content(
        puzzle +
        ". Diretamente resolva o problema: Quem podemos garantir que é cavaleiro e quem é patife? "
        "Responda em ordem alfabética. Para problemas impossíveis, retorne: Inconsistente para todas as pessoas."
    )

    print(resposta.text)

    # LLM (COM Z3)
    print("\nCOM Z3")
    resposta_direta = model.generate_content(
        puzzle +
        " Agora usando Z3, traduza o problema e retorne apenas o resultado direto, "
        "ex.: A: Cavaleiro; B: Patife; C: Indeterminado."
    )
    print(resposta_direta.text)

    # Z3 REAL
    print("\nZ3: Consequências Lógicas (O que é garantido)")
    try:
        variables, restrictions = parse_puzzle_to_z3(puzzle)
        consequencias = logical_consequences(variables, restrictions)

        for nome, status in consequencias.items():
            print(f"{nome}: {status}")

        # Compare WITHOUT Z3
        match_sem = compare_results(resposta.text, consequencias)
        salva_comparacao(arquivo_escolhido, puzzle, resposta.text, consequencias, match_sem)

        if match_sem:
            print("\nLLM ACERTOU O PUZZLE SEM Z3")
        else:
            print("\nLLM ERROU O PUZZLE SEM Z3")

        # Compare WITH Z3
        match_com = compare_results(resposta_direta.text, consequencias)
        salva_comparacao(arquivo_escolhido, puzzle, resposta_direta.text, consequencias, match_com)

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

import os
import argparse
from dotenv import load_dotenv
import google.generativeai as genai
import random
import json
from datetime import datetime
from solverz3 import *
from save_results import *
from flask import Flask, request, jsonify
import time
import io
import sys


# ============================================================
# 1. ORIGINAL SOLVER (kept exactly as your team made it)
# ============================================================

def solver(puzzle_arg=None):

    # CLI args to optionally pick a specific puzzle file
    parser = argparse.ArgumentParser(description="Resolve puzzles de cavaleiros e patifes")
    parser.add_argument("--puzzle", help="Nome do arquivo .txt em puzzles/ a ser usado (ex: puzzle1.txt)")
    args = parser.parse_args()

    # Loading environment variables
    load_dotenv()

    # Accessing API KEY
    api_key = os.getenv("API_KEY")

    if api_key:
        print("Chave de API carregada com sucesso")
    else:
        print("Chave de API não encontrada no arquivo .env.")
        return

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    # Puzzle via argumento
    parser = argparse.ArgumentParser(
        description="Executa a lógica do Gemini para um puzzle específico."
    )

    parser.add_argument(
        "-p",
        "--puzzle",
        help="Nome do arquivo do puzzle ou path",
    )

    args = parser.parse_args()

    puzzles_dir = "puzzles"

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
        arquivos = sorted(
            [f for f in os.listdir(puzzles_dir) if f.endswith(".txt")]
        )
        if not arquivos:
            print("Nenhum arquivo .txt encontrado na pasta 'puzzles'.")
            return
        arquivo_escolhido = arquivos[0]
        caminho_puzzle = os.path.join(puzzles_dir, arquivo_escolhido)

    # List .txt files within folder
    arquivos = [f for f in os.listdir(puzzles_dir) if f.endswith(".txt")]

    if not arquivos:
        print("Nenhum arquivo .txt encontrado na pasta 'puzzles'.")
        return

    # Choose puzzle: from CLI or random
    if args.puzzle:
        if args.puzzle not in arquivos:
            print(f"Arquivo {args.puzzle} não encontrado na pasta 'puzzles'.")
            return
        arquivo_escolhido = args.puzzle
    else:
        arquivo_escolhido = random.choice(arquivos)
    caminho_puzzle = os.path.join(puzzles_dir, arquivo_escolhido)

    # Read the puzzle content 
    with open(caminho_puzzle, "r", encoding="utf-8") as f:
        puzzle = f.read().strip()

    # ======= LLM (SEM Z3) =======
    resposta = model.generate_content(
        puzzle + ". Diretamente resolva o problema: Quem podemos garantir (Ou quem é consequência lógica) que é cavaleiro e quem é patife?"
        " Responda de forma direta, poucas linhas, exemplo: A: Cavaleiro\n B: Patife\n C: Indeterminado\nNão é necessário exibir a cadeia de pensamento, sempre em ordem alfabética,"
        " para problemas impossíveis, retorne: Inconsistente para todas as pessoas"
    )

    print(puzzle)
    print("\nSEM Z3")
    print(resposta.text)

    # ======= LLM (COM Z3) =======
    resposta_direta = model.generate_content(
        puzzle + " Agora com ajuda da biblioteca Z3, traduza o problema para Z3 e resolva (Não é necessário envio do código): "
        "Quem podemos garantir que é cavaleiro e quem é patife? Responda de forma direta, poucas linhas, apenas informando o que é "
        "garantido ou não exemplo: A: Cavaleiro\n B: Patife\n C: Indeterminado\n"
        "Não é necessário exibir a cadeia de pensamento, sempre em ordem alfabética, para problemas impossíveis, retorne: Inconsistente para todas as pessoas"
    )

    print("\nCOM Z3")
    print(resposta_direta.text)

    # ======= Z3 (REAL) =======
    try:
        variables, restrictions = parse_puzzle_to_z3(puzzle)
        resultado_z3 = generic_solver(variables, restrictions)

        print("\nZ3: Consequências Lógicas (O que é garantido)")
        consequencias = logical_consequences(variables, restrictions)

        for nome, status in consequencias.items():
            print(f"{nome}: {status}")

        # Compare without Z3 (registro principal)
        match = compare_results(resposta.text, consequencias)
        salva_comparacao(arquivo_escolhido, puzzle, resposta.text, consequencias, match)

        if match:
            print("\nLLM ACERTOU O PUZZLE SEM Z3")
        else:
            print("\nLLM ERROU O PUZZLE SEM Z3")

        # Compare with Z3 (apenas exibição, não salva em results.jsonl para evitar duplicatas)
        match = compare_results(resposta_direta.text, consequencias)
        if match:
            print("\nLLM ACERTOU O PUZZLE COM Z3")
        else:
            print("\nLLM ERROU O PUZZLE COM Z3")

    except Exception as e:
        print(f"Erro ao resolver com Z3: {e}")



# ============================================================
# 2. STREAMING WRAPPER — DO NOT TOUCH SOLVER LOGIC
# ============================================================

def solve(puzzle_arg=None):
    """
    Wrapper that captures all prints inside solver() and converts them into yields.
    This allows the web UI to stream the output EXACTLY like the terminal,
    without modifying any logic that your friends built.
    """
    buffer = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buffer

    # Run original solver code
    try:
        if puzzle_arg:
            solver(puzzle_arg)
        else:
            solver()
    except Exception as e:
        yield f"Erro: {e}"

    # Restore terminal
    sys.stdout = old_stdout

    # Yield everything solver printed
    output = buffer.getvalue().splitlines()
    for line in output:
        yield line



# ============================================================
# 3. TERMINAL MODE (unchanged, safe)
# ============================================================

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--puzzle", help="Nome do puzzle")
    args = parser.parse_args()

    # Terminal runs solver() normally — NO BEHAVIOR CHANGED
    if args.puzzle:
        solver(args.puzzle)
    else:
        solver()

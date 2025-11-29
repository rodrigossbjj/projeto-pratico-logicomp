import os
import argparse
from dotenv import load_dotenv
from openai import OpenAI
import json
from datetime import datetime
from solverz3 import *


load_dotenv()

openai_key = os.getenv("OPENAI_API_KEY")
if not openai_key:
    print("Chave OPENAI_API_KEY não encontrada no .env.")
    exit(1)

client = OpenAI(api_key=openai_key)

puzzle_parser = argparse.ArgumentParser(
    description="Executa a lógica do GPT para um puzzle."
)
puzzle_parser.add_argument(
    "-p",
    "--puzzle",
    help="Nome do arquivo do puzzle ou caminho completo!",
)
args = puzzle_parser.parse_args()

puzzles_dir = "puzzles"

if args.puzzle:
    puzzle_arg = args.puzzle if args.puzzle.endswith(".txt") else f"{args.puzzle}.txt"
    if os.path.isabs(puzzle_arg):
        caminho_puzzle = puzzle_arg
    else:
        caminho_puzzle = os.path.join(puzzles_dir, puzzle_arg)

    if not os.path.exists(caminho_puzzle):
        raise FileNotFoundError(f"Puzzle '{puzzle_arg}' não encontrado!")

    puzzle_name = os.path.basename(caminho_puzzle)
else:
    arquivos = sorted(
        [f for f in os.listdir(puzzles_dir) if f.endswith(".txt")]
    )
    if not arquivos:
        raise FileNotFoundError("Nenhum arquivo .txt encontrado na pasta 'puzzles'.")
    puzzle_name = arquivos[0]
    caminho_puzzle = os.path.join(puzzles_dir, puzzle_name)

with open(caminho_puzzle, "r", encoding="utf-8") as fp:
    puzzle_text = fp.read().strip()

prompt_base = (
    puzzle_text
    + ". Diretamente resolva o problema: Quem podemos garantir que é cavaleiro e quem é patife?"
)
full_prompt = (
    prompt_base
    + " Agora com ajuda da biblioteca Z3, traduza o problema para Z3 e resolva: "
    "Quem podemos garantir que é cavaleiro e quem é patife? Retorne o resultado assim por ex: A: cavaleiro"
)

print(prompt_base)

response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[
        {"role": "user", "content": full_prompt},
    ],
)

llm_answer = response.choices[0].message.content
print(llm_answer)

try:
    vars_z3, restrictions = parse_puzzle_to_z3(prompt_base)
    resultado_z3 = generic_solver(vars_z3, restrictions)
    print("Resposta correta (Z3 real)\n")
    if isinstance(resultado_z3, dict):
        for pessoa, valor in resultado_z3.items():
            print(f"{pessoa}: {'Cavaleiro' if valor else 'Patife'}")
    else:
        print(resultado_z3)

    print("\nConsequências Lógicas (O que é garantido)")
    consequencias = logical_consequences(vars_z3, restrictions)
    for nome, status in consequencias.items():
        print(f"{nome}: {status}")
except Exception as exc:
    print(f"Erro ao resolver com Z3: {exc}")
    raise


def compare_results(llm_answer: str, z3_answer: str) -> bool:
    llm_answer = llm_answer.strip().lower()
    z3_answer = z3_answer.strip().lower()

    return any(
        [
            "cavaleiro" in llm_answer and "cavaleiro" in z3_answer,
            "patife" in llm_answer and "patife" in z3_answer,
            llm_answer == z3_answer,
        ]
    )


def salva_comparacao(puzzle_name, puzzle_text, llm_answer, z3_answer, match):
    resultados_dir = "resultados"
    os.makedirs(resultados_dir, exist_ok=True)

    txt_path = os.path.join(resultados_dir, "comparacoes_gpt.txt")
    json_path = os.path.join(resultados_dir, "results_gpt.jsonl")

    with open(txt_path, "a", encoding="utf-8") as f:
        f.write(f"Puzzle: {puzzle_name}\n")
        f.write(f"Texto do Puzzle:\n{puzzle_text}\n")
        f.write(f"Resposta GPT:\n{llm_answer}\n")
        f.write(f"Resposta Z3:\n{z3_answer}\n")
        f.write(f"Correspondência: {'Sim' if match else 'Não'}\n")
        f.write("=" * 40 + "\n")

    result = {
        "timestamp": datetime.now().isoformat(),
        "puzzle_file": puzzle_name,
        "puzzle_text": puzzle_text,
        "llm_answer": llm_answer,
        "z3_answer": z3_answer,
        "match": match,
        "model": "gpt-4o-mini",
    }
    with open(json_path, "a", encoding="utf-8") as jf:
        jf.write(json.dumps(result, ensure_ascii=False) + "\n")


match = compare_results(llm_answer, str(resultado_z3))
salva_comparacao(puzzle_name, prompt_base, llm_answer, str(resultado_z3), match)

if match:
    print(f"\n✅ O resultado da IA(GPT) COINCIDE com o resultado do Z3!")
else:
    print(f"\n❌ A IA(GPT) ERROU! Veja detalhes salvos em resultados/results.jsonl")


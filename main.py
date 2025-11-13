import os
from dotenv import load_dotenv
import google.generativeai as genai
import random
import json
from datetime import datetime
from solverz3 import *

#Loading environment variables from .env file
load_dotenv()
#Accessing environment variable API_KEY
api_key = os.getenv("API_KEY")
#Checking if API_KEY was successfully loaded
if api_key:
    print("Chave de API carregada com sucesso")
else:
    print("Chave de API não encontrada no arquivo .env.")
    exit()

genai.configure(api_key=api_key)
model = genai.GenerativeModel("gemini-2.5-flash")

puzzles_dir = "puzzles"

# List .txt files within folder
arquivos = [f for f in os.listdir(puzzles_dir) if f.endswith(".txt")]

if not arquivos:
    raise FileNotFoundError("Nenhum arquivo .txt encontrado na pasta 'puzzles'.")

# Choose a random puzzle
arquivo_escolhido = random.choice(arquivos)
caminho_puzzle = os.path.join(puzzles_dir, arquivo_escolhido)

# Read the puzzle content 
with open(caminho_puzzle, "r", encoding="utf-8") as f:
    puzzle = f.read().strip()

# Strategy for not asking too many questions
puzzle += ". Diretamente resolva o problema: Quem podemos garantir que é cavaleiro e quem é patife?"

# resposta = model.generate_content(puzzle)

print(puzzle)
# print(resposta.text)

resposta_direta = model.generate_content(puzzle + " Agora com ajuda da biblioteca Z3, traduza o problema para Z3 e resolva: Quem podemos garantir que é cavaleiro e quem é patife? Retorne o resultado assim por ex: A: cavaleiro")

print(resposta_direta.text)

# Z3 with correct answer
try:
    variables, restrictions = parse_puzzle_to_z3(puzzle)
    resultado_z3 = generic_solver(variables, restrictions)

    # print(variables)
    # print (restrictions)
    print("Resposta correta (Z3 real)\n")
    if isinstance(resultado_z3, dict):
        for p, v in resultado_z3.items():
            print(f"{p}: {'Cavaleiro' if v else 'Patife'}")
    else:
        print(resultado_z3)

    print("\nConsequências Lógicas (O que é garantido)")
    consequencias = logical_consequences(variables, restrictions)
    for nome, status in consequencias.items():
        print(f"{nome}: {status}")
except Exception as e:
    print(f"Erro ao resolver com Z3: {e}")

def compare_results(llm_answer: str, z3_answer: str) -> bool:
    """Comparar o resultado do LLM com o resultado do Z3."""
    llm_answer = llm_answer.strip().lower()
    z3_answer = z3_answer.strip().lower()

    return any([
        "cavaleiro" in llm_answer and "cavaleiro" in z3_answer,
        "patife" in llm_answer and "patife" in z3_answer,
        llm_answer == z3_answer
    ])


def salva_comparacao(puzzle_name, puzzle_text, llm_answer, z3_answer, match):
    """Salva a comparação entre as respostas do LLM e do Z3 em um arquivo jsonl e txt."""
    resultados_dir = "resultados"
    os.makedirs(resultados_dir, exist_ok=True)

    txt_path = os.path.join(resultados_dir, "comparacoes.txt")
    json_path = os.path.join(resultados_dir, "results.jsonl")

    # Salva em texto
    with open(txt_path, "a", encoding="utf-8") as f:
        f.write(f"Puzzle: {puzzle_name}\n")
        f.write(f"Texto do Puzzle:\n{puzzle_text}\n")
        f.write(f"Resposta LLM:\n{llm_answer}\n")
        f.write(f"Resposta Z3:\n{z3_answer}\n")
        f.write(f"Correspondência: {'Sim' if match else 'Não'}\n")
        f.write("=" * 40 + "\n")

    # Salva em JSONL
    result = {
        "timestamp": datetime.now().isoformat(),
        "puzzle_file": puzzle_name,
        "puzzle_text": puzzle_text,
        "llm_answer": llm_answer,
        "z3_answer": z3_answer,
        "match": match
    }
    with open(json_path, "a", encoding="utf-8") as jf:
        jf.write(json.dumps(result, ensure_ascii=False) + "\n")


# =====================================================
# 🔹 6. Comparação e Salvamento de Resultados
# =====================================================
# (put this OUTSIDE the function, same indent as try/except)

match = compare_results(resposta_direta.text, str(resultado_z3))
salva_comparacao(arquivo_escolhido, puzzle, resposta_direta.text, str(resultado_z3), match)

if match:
    print(f"\n✅ O resultado da IA COINCIDE com o resultado do Z3!")
else:
    print(f"\n❌ A IA ERROU! Veja detalhes salvos em resultados/results.jsonl")

    

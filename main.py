import os
from dotenv import load_dotenv
import google.generativeai as genai
import random
import json
from datetime import datetime
from solverz3 import *
from save_results import * 

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

resposta = model.generate_content(puzzle + ". Diretamente resolva o problema: Quem podemos garantir (Ou quem é consequência lógica) que é cavaleiro e quem é patife?"
                                " Responda de forma direta, poucas linhas, exemplo: A: Cavaleiro\n B: Patife\n C: Indeterminado\nNáo é necessário exibir a cadeia de pensamento")
print(puzzle)
print("SEM Z3")
print(resposta.text)

resposta_direta = model.generate_content(puzzle + " Agora com ajuda da biblioteca Z3, traduza o problema para Z3 e resolva (Não é necessário envio do código): "
                                        "Quem podemos garantir que é cavaleiro e quem é patife? Responda de forma direta, poucas linhas, apenas informando o que é "
                                        "garantido ou não exemplo: A: Cavaleiro\n B: Patife\n C: Indeterminado\n"
                                        "Náo é necessário exibir a cadeia de pensamento")

print("COM Z3")
print(resposta_direta.text)

# Z3 with correct answer
try:
    variables, restrictions = parse_puzzle_to_z3(puzzle)
    resultado_z3 = generic_solver(variables, restrictions)

    print("Resposta correta (Z3 real)\n")
    if isinstance(resultado_z3, dict):
        for p, v in resultado_z3.items():
            print(f"{p}: {'Cavaleiro' if v else 'Patife'}")
    else:
        print(resultado_z3)

    print("\nConsequências Lógicas (O que é garantido)")
    consequencias = logical_consequences(variables, restrictions)
    match = compare_results(resposta.text, consequencias)
    salva_comparacao(arquivo_escolhido, puzzle, resposta.text, consequencias, match)
    for nome, status in consequencias.items():
        print(f"{nome}: {status}")
except Exception as e:
    print(f"Erro ao resolver com Z3: {e}")


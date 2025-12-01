import os
from dotenv import load_dotenv
import google.generativeai as genai
import random
import json
from datetime import datetime
from solverz3 import *
from save_results import * 

def normalize_answer(text: str) -> dict:
    """
    Extrai apenas linhas no formato 'A: Cavaleiro' em dict: {"A": "cavaleiro"}
    """
    result = {}
    for line in text.splitlines():
        if ":" in line:
            left, right = line.split(":", 1)
            person = left.strip().upper()
            status = right.strip().lower()

            if len(person) == 1 and person.isalpha():
                result[person] = status
    return result


def compare_results(llm_answer: str, z3_consequencias: dict) -> bool:
    """
    Compara apenas o que é garantido pelo Z3:
    - Se Z3 diz 'Cavaleiro', LLM deve dizer 'cavaleiro'
    - Se Z3 diz 'Patife', LLM deve dizer 'patife'
    - Se Z3 diz 'Indeterminado', ignoramos (não conta como erro)
    """
    llm_dict = normalize_answer(llm_answer)

    for person, status in z3_consequencias.items():
        status = status.lower()

        # Indeterminado → não pode ser cobrado do LLM
        # if "indeterminado" in status:
        #     continue

        # Normaliza o status do Z3 para apenas "cavaleiro" ou "patife"
        if "cavaleiro" in status:
            expected = "cavaleiro"
        elif "patife" in status:
            expected = "patife"
        else:
            expected = "indeterminado"

        # Se LLM não respondeu aquela letra ou divergiu, falha
        if llm_dict.get(person) != expected:
            return False

    return True

def salva_comparacao(puzzle_name, puzzle_text, llm_answer, z3_consequencias, match):
    os.makedirs("resultados", exist_ok=True)
 
    short_llm = normalize_answer(llm_answer)

    # JSONL curto
    with open("resultados/results.jsonl", "a", encoding="utf-8") as jf:
        jf.write(json.dumps({
            "puzzle": puzzle_name,
            "llm": short_llm,
            "z3_consequencias": z3_consequencias,
            "match": match
        }, ensure_ascii=False) + "\n")

    # TXT curto
    with open("resultados/comparacoes.txt", "a", encoding="utf-8") as f:
        f.write(f"{puzzle_name} | MATCH: {match}\n")
        f.write(f"LLM: {short_llm}\n")
        f.write(f"Z3:  {z3_consequencias}\n")
        f.write("-" * 30 + "\n")

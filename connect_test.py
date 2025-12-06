import google.generativeai as genai
from openai import OpenAI
from dotenv import load_dotenv
import os

# Loading environment variables from .env file
load_dotenv()

# Teste Gemini
print("=" * 50)
print("Testando conexão com Gemini...")
print("=" * 50)

apiKey = os.getenv("API_KEY")
if apiKey:
    genai.configure(api_key=apiKey)
    model = genai.GenerativeModel("gemini-2.5-flash")
    resposta = model.generate_content("Explique o que é um algoritmo em poucas palavras.")
    print("✅ Gemini conectado com sucesso!")
    print(f"Resposta: {resposta.text}\n")
else:
    print("❌ API_KEY não encontrada no arquivo .env\n")

# Teste GPT
print("=" * 50)
print("Testando conexão com GPT...")
print("=" * 50)

openai_key = os.getenv("OPENAI_API_KEY")
if openai_key:
    client = OpenAI(api_key=openai_key)
    resposta_gpt = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "user", "content": "Explique o que é um algoritmo em poucas palavras."}
        ]
    )
    print("✅ GPT conectado com sucesso!")
    print(f"Resposta: {resposta_gpt.choices[0].message.content}\n")
else:
    print("❌ OPENAI_API_KEY não encontrada no arquivo .env\n")
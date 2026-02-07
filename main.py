import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os
import time

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"})

def perguntar_ia(ticker, variacao, preco):
    try:
        genai.configure(api_key=GEMINI_KEY)
        # Na v0.8.6, usamos apenas o nome do modelo
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        time.sleep(5) 
        prompt = f"Ação {ticker} {variacao}% preço {preco}. Explique o motivo em 1 frase curta em Português."
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Erro de permissão: Verifique se a chave é de um 'Novo Projeto'."

def executar_itisinvest():
    print("📡 ITISI Invest: Teste final com Chave Nova...")
    
    # Teste rápido apenas com os principais para não estourar a quota
    info = ""
    for t in ["ACHR", "NVDA", "MSTR"]:
        try:
            acao = yf.Ticker(t)
            p = acao.history(period="1d")['Close'].iloc[-1]
            # Simulando variação para o prompt
            analise = perguntar_ia(t, "relevante", round(p, 2))
            info += f"📈 *{t}*\n👉 {analise}\n\n"
        except: continue

    enviar_telegram(f"🧪 *RELATÓRIO FINAL*\n\n{info}")

if __name__ == "__main__":
    executar_itisinvest()

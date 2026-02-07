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
    # REMOVEMOS O TRY/EXCEPT PARA VER O ERRO NO LOG
    genai.configure(api_key=GEMINI_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    time.sleep(5) # Evitar bloqueio de velocidade
    
    prompt = f"Ação {ticker} ({variacao}%). Preço ${preco}. Explique o motivo em 10 palavras em Português."
    response = model.generate_content(prompt)
    return response.text.strip()

def executar_itisinvest():
    print("📡 Teste de Diagnóstico Crítico...")
    
    # Exemplo rápido com apenas 1 ação para testar a IA
    try:
        ticker = "NVDA"
        acao = yf.Ticker(ticker)
        p_atual = acao.history(period="1d")['Close'].iloc[-1]
        
        analise = perguntar_ia(ticker, "7.87", round(p_atual, 2))
        
        msg = f"✅ IA FUNCIONOU!\n\n🚀 *{ticker}*\n👉 {analise}"
        enviar_telegram(msg)
        print("Sucesso!")
        
    except Exception as e:
        erro_msg = f"❌ FALHA CRÍTICA:\n{str(e)}"
        enviar_telegram(erro_msg)
        print(erro_msg)

if __name__ == "__main__":
    executar_itisinvest()

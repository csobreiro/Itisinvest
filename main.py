import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os
import time

# --- CONFIGURAÇÕES ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"})

def perguntar_ia(ticker, preco):
    try:
        # Debug para o log do GitHub (não vai para o Telegram)
        if not GEMINI_KEY:
            return "Erro: Chave API não encontrada nos Secrets."
        
        genai.configure(api_key=GEMINI_KEY)
        
        # Tentamos o modelo 1.0 Pro primeiro - é o mais compatível de todos
        model = genai.GenerativeModel('gemini-1.0-pro')
        
        time.sleep(2) # Pausa curta
        
        prompt = f"A ação {ticker} custa ${preco}. Escreva uma frase curta sobre o setor desta empresa em Português."
        
        # Chamada ultra simples
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        return "IA respondeu mas o texto está vazio."
        
    except Exception as e:
        # Se falhar o Pro, tentamos o Flash como última esperança
        try:
            model_f = genai.GenerativeModel('gemini-1.5-flash')
            return model_f.generate_content(prompt).text.strip()
        except:
            return f"Erro final: {str(e)[:40]}"

def executar_itisinvest():
    print(f"📡 Debug: Chave começa com {GEMINI_KEY[:4]}... (Verifique se coincide)")
    
    info = ""
    # Teste apenas com NVDA para isolar o problema
    try:
        t = "NVDA"
        acao = yf.Ticker(t)
        p = acao.history(period="1d")['Close'].iloc[-1]
        
        analise = perguntar_ia(t, round(p, 2))
        info = f"📈 *{t}*\n👉 {analise}"
    except Exception as e:
        info = f"Erro no Yahoo Finance: {e}"

    enviar_telegram(f"🧪 *TESTE DEFINITIVO*\n\n{info}")

if __name__ == "__main__":
    executar_itisinvest()

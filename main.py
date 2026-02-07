import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os

# --- CONFIGURAÇÕES ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configurar Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, data=payload)

def analisar_itisinvest(ticker):
    print(f"A analisar {ticker}...")
    try:
        acao = yf.Ticker(ticker)
        hist = acao.history(period="60d")
        if hist.empty: return

        preco_atual = hist['Close'].iloc[-1]
        ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]

        # Só avança se o preço estiver acima da média (Sinal de força)
        if preco_atual > ma20:
            # MÉTODO CORRIGIDO PARA NOTÍCIAS:
            news_list = acao.news
            # Tenta pegar os títulos de forma segura
            titulos = ""
            if news_list:
                for n in news_list[:3]:
                    titulos += f"- {n.get('title', n.get('content', {}).get('title', 'Sem título'))}\n"

            prompt = (f"Analisa a ação {ticker}. Preço: ${preco_atual:.2f}. "
                      f"Notícias recentes:\n{titulos}\n"
                      f"Diz em 3 tópicos: Vale o risco comprar hoje? Responde em Português.")

            response = model.generate_content(prompt)
            
            msg = (f"🤖 *itisinvest ALERT*\n\n"
                   f"📈 *Ativo:* {ticker}\n"
                   f"💰 *Preço:* ${preco_atual:.2f}\n\n"
                   f"🧠 *Análise da IA:*\n{response.text}")
            
            enviar_telegram(msg)
    except Exception as e:
        print(f"Erro ao analisar {ticker}: {e}")

watchlist = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN"]

if __name__ == "__main__":
    for papel in watchlist:
        analisar_itisinvest(papel)

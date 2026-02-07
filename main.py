import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os

# --- CONFIGURAÇÕES DE AMBIENTE (Segurança) ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configurar o Cérebro (Gemini)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def analisar_itisinvest(ticker):
    print(f"A analisar {ticker}...")
    acao = yf.Ticker(ticker)
    
    # 1. Dados Técnicos (Últimos 60 dias)
    hist = acao.history(period="60d")
    if hist.empty: return
    
    preco_atual = hist['Close'].iloc[-1]
    ma20 = hist['Close'].rolling(window=20).mean().iloc[-1]
    ma50 = hist['Close'].rolling(window=50).mean().iloc[-1]

    # 2. Estratégia: Filtro de Tendência (Preço acima das médias)
    # Podes mudar esta lógica conforme quiseres
    if preco_atual > ma20:
        sinal = "TENDÊNCIA DE ALTA" if preco_atual > ma50 else "RECUPERAÇÃO"
        
        # 3. Análise de Contexto com IA
        noticias = acao.news[:3]
        titulos = "\n".join([n['title'] for n in noticias])
        
        prompt = (f"Como analista financeiro, analisa a ação {ticker}. "
                  f"Preço atual: {preco_atual:.2f}. Tendência: {sinal}. "
                  f"Notícias recentes: {titulos}. "
                  f"Diz-me em 3 tópicos curtos: Vale a pena o risco de compra hoje? "
                  f"Responde em Português de Portugal.")

        try:
            response = model.generate_content(prompt)
            analise_ia = response.text
            
            # 4. Formatar e Enviar Mensagem
            msg = (f"🤖 *itisinvest ALERT*\n\n"
                   f"📈 *Ativo:* {ticker}\n"
                   f"💰 *Preço:* ${preco_atual:.2f}\n"
                   f"📊 *Sinal:* {sinal}\n\n"
                   f"🧠 *Análise da IA:*\n{analise_ia}")
            
            enviar_telegram(msg)
        except Exception as e:
            print(f"Erro na IA para {ticker}: {e}")

# --- EXECUÇÃO ---
# Lista de ações que queres que o itisinvest vigie
watchlist = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN"]

if __name__ == "__main__":
    for papel in watchlist:
        analisar_itisinvest(papel)
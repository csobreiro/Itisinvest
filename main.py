import yfinance as yf
import pandas as pd
import requests
import os
from groq import Groq

# --- CONFIGURAÇÕES ---
GROQ_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=20)
    except Exception as e:
        print(f"Erro Telegram: {e}")

def perguntar_ia(ticker, preco):
    try:
        if not GROQ_KEY:
            return "Erro: GROQ_API_KEY não configurada."
            
        client = Groq(api_key=GROQ_KEY)
        prompt = f"Ação {ticker} preço ${preco}. Explique brevemente o que a empresa faz e a tendência em 1 frase em Português."
        
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192",
            temperature=0.5
        )
        return chat_completion.choices[0].message.content.strip()
    except Exception as e:
        return f"IA indisponível ({str(e)[:30]})"

def executar_itisinvest():
    print("📡 Iniciando Scan...")
    
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        df = pd.read_csv('carteira.csv')
        df.columns = df.columns.str.strip().str.lower()
        
        for _, row in df.iterrows():
            try:
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                
                # Dados do Yahoo Finance
                acao = yf.Ticker(t)
                p_atual = acao.history(period="1d")['Close'].iloc[-1]
                perf = ((p_atual - p_compra) / p_compra) * 100
                
                # Análise da Groq
                analise = perguntar_ia(t, round(p_atual, 2))
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n   👉 {analise}\n\n"
            except: continue
    else:
        info_carteira = "⚠️ Carteira.csv não encontrado."

    msg = f"📦 *ITISI Invest - RELATÓRIO (GROQ)*\n───────────────────\n{info_carteira}"
    enviar_telegram(msg)
    print("✅ Concluído!")

if __name__ == "__main__":
    executar_itisinvest()

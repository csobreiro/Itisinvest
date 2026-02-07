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
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, data=payload, timeout=25)

def perguntar_ia(ticker, variacao, preco):
    try:
        # Tenta reconfigurar a cada chamada para garantir conexão
        genai.configure(api_key=GEMINI_KEY)
        model = genai.GenerativeModel("gemini-1.5-flash")
        
        time.sleep(4) # Espera generosa para a conta gratuita
        
        prompt = f"Analise a ação {ticker} que variou {variacao}% custando ${preco}. O que explica isso em 10 palavras?"
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        # Se falhar, ele agora vai dizer o erro real na mensagem do Telegram!
        erro_msg = str(e)[:50]
        return f"Erro na IA ({erro_msg})"

def executar_itisinvest():
    print("📡 Diagnóstico de IA em curso...")
    
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        df_cart = pd.read_csv('carteira.csv')
        for _, row in df_cart.iterrows():
            try:
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                
                acao = yf.Ticker(t)
                p_atual = acao.history(period="1d")['Close'].iloc[-1]
                perf = ((p_atual - p_compra) / p_compra) * 100
                
                analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                info_carteira += f"🔴 *{t}* | {perf:.2f}%\n   👉 {analise}\n\n"
            except: continue

    radar_investimentos = ""
    for t in ["NVDA", "TSLA"]:
        try:
            acao = yf.Ticker(t)
            v = ((acao.history(period="2d")['Close'].iloc[-1] / acao.history(period="2d")['Close'].iloc[-2]) - 1) * 100
            analise_r = perguntar_ia(t, round(v, 2), "MERCADO")
            radar_investimentos += f"🚀 *{t}* (+{v:.2f}%)\n   👉 {analise_r}\n\n"
        except: continue

    msg = f"🧪 *TESTE DE DIAGNÓSTICO IA*\n\n{info_carteira}{radar_investimentos}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

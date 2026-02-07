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
        genai.configure(api_key=GEMINI_KEY)
        # Usamos o modelo mais estável
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        time.sleep(4) # Intervalo para evitar bloqueio por velocidade
        
        prompt = f"Ação {ticker} ({variacao}%). Preço ${preco}. Resuma o motivo e tendência em 15 palavras em Português."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"Aguardando ativação da API... ({str(e)[:15]})"

def executar_itisinvest():
    print("📡 ITISI Invest: Testando nova chave API...")
    
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
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n   👉 {analise}\n\n"
            except: continue

    radar_investimentos = ""
    for t in ["NVDA", "TSLA"]:
        try:
            acao = yf.Ticker(t)
            v = ((acao.history(period="2d")['Close'].iloc[-1] / acao.history(period="2d")['Close'].iloc[-2]) - 1) * 100
            analise_r = perguntar_ia(t, round(v, 2), round(acao.history(period="1d")['Close'].iloc[-1], 2))
            radar_investimentos += f"🚀 *{t}* (+{v:.2f}%)\n   👉 {analise_r}\n\n"
        except: continue

    msg = f"📦 *ITISI Invest - RELATÓRIO*\n───────────────────\n{info_carteira}{radar_investimentos}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

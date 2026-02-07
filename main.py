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

def perguntar_ia(ticker, variacao, preco):
    try:
        genai.configure(api_key=GEMINI_KEY)
        
        # Testamos o nome mais simples possível
        # Se a biblioteca estiver atualizada, isto funciona 100%
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        time.sleep(5) 
        prompt = f"Ação {ticker} {variacao}% preço {preco}. Motivo e tendência em 10 palavras em Português."
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Se der erro, vamos ver a versão da biblioteca no log
        import google.generativeai as gai
        return f"Erro (Lib v{gai.__version__}): {str(e)[:20]}"

def executar_itisinvest():
    print("📡 ITISI Invest: Forçando atualização de rota...")
    
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        df = pd.read_csv('carteira.csv')
        df.columns = df.columns.str.strip().str.lower()
        for _, row in df.iterrows():
            try:
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                acao = yf.Ticker(t)
                p_atual = acao.history(period="1d")['Close'].iloc[-1]
                perf = ((p_atual - p_compra) / p_compra) * 100
                analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                info_carteira += f"🔴 *{t}* | {perf:.2f}%\n   👉 {analise}\n\n"
            except: continue

    radar = ""
    for t in ["NVDA", "TSLA", "MSTR"]:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            v = ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100
            if v > 1.5:
                res = perguntar_ia(t, round(v, 2), round(h['Close'].iloc[-1], 2))
                radar += f"🚀 *{t}* (+{v:.2f}%)\n   👉 {res}\n\n"
        except: continue

    msg = f"📦 *RELATÓRIO DE DIAGNÓSTICO*\n\n{info_carteira}{radar}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

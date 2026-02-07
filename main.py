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
    requests.post(url, data=payload)

def perguntar_ia(ticker, preco):
    try:
        genai.configure(api_key=GEMINI_KEY)
        # Usamos o nome oficial completo para evitar o erro 404
        model = genai.GenerativeModel('models/gemini-1.5-flash')
        
        time.sleep(5) # Pausa para quota gratuita
        
        prompt = f"Ação {ticker} preco ${preco}. Explique a empresa e tendência em 1 frase em Português."
        response = model.generate_content(prompt)
        
        if response.text:
            return response.text.strip()
        return "Análise técnica indisponível."
    except Exception as e:
        # Se o 1.5 falhar, tentamos o 1.0 pro como último recurso
        try:
            model_alt = genai.GenerativeModel('models/gemini-1.0-pro')
            return model_alt.generate_content(prompt).text.strip()
        except:
            return f"Erro: {str(e)[:20]}"

def executar_itisinvest():
    print("📡 ITISI Invest: Gerando relatório com rota oficial...")
    
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        df = pd.read_csv('carteira.csv')
        df.columns = df.columns.str.strip().str.lower()
        for _, row in df.iterrows():
            try:
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                
                # Yahoo Finance
                acao = yf.Ticker(t)
                h = acao.history(period="1d")
                if h.empty: continue
                
                p_atual = h['Close'].iloc[-1]
                perf = ((p_atual - p_compra) / p_compra) * 100
                
                # IA
                analise = perguntar_ia(t, round(p_atual, 2))
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n   👉 {analise}\n\n"
            except: continue

    msg = f"📦 *ITISI Invest - RELATÓRIO FINAL*\n───────────────────\n{info_carteira}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

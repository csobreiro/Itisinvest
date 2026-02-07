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
    try:
        requests.post(url, data=payload, timeout=25)
    except Exception as e:
        print(f"Erro de rede: {e}")

def perguntar_ia(ticker, variacao, preco):
    try:
        genai.configure(api_key=GEMINI_KEY)
        # Versão 'latest' para evitar erros de rotas obsoletas
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        # Pausa de segurança para conta gratuita
        time.sleep(4) 
        
        prompt = f"Ação {ticker} {variacao}% preço ${preco}. Resuma o motivo da variação e tendência em 10 palavras em Português."
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        return "Análise técnica: Monitorize volume e suportes."
        
    except Exception as e:
        # Se falhar, mostra o erro técnico para diagnóstico
        erro_curto = str(e)[:30]
        return f"Aguardando API: {erro_curto}"

def executar_itisinvest():
    print("📡 ITISI Invest: A processar dados de mercado...")
    
    # --- PARTE 1: CARTEIRA ---
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        try:
            df = pd.read_csv('carteira.csv')
            df.columns = df.columns.str.strip().str.lower()
            
            for _, row in df.iterrows():
                try:
                    t = str(row['ticker']).strip().upper()
                    p_compra = float(row['preco_compra'])
                    qtd = float(row.get('quantidade', 1))
                    
                    acao = yf.Ticker(t)
                    p_atual = acao.history(period="1d")['Close'].iloc[-1]
                    perf = ((p_atual - p_compra) / p_compra) * 100
                    
                    analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                    
                    emoji = "🟢" if perf >= 0 else "🔴"
                    info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n"
                    info_carteira += f"   • Valor: ${p_atual*qtd:.2f}\n"
                    info_carteira += f"   👉 {analise}\n\n"
                except: continue
        except Exception as e:
            info_carteira = f"⚠️ Erro no CSV: {str(e)[:20]}\n"
    else:
        info_carteira = "ℹ️ Crie o ficheiro 'carteira.csv'.\n"

    # --- PARTE 2: RADAR ---
    radar = ""
    for t in ["NVDA", "TSLA", "MSTR", "AMD", "PLTR"]:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            v = ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100
            if v > 1.5:
                resumo = perguntar_ia(t, round(v, 2), round(h['Close'].iloc[-1], 2))
                radar += f"🚀 *{t}* (+{v:.2f}%)\n   👉 {resumo}\n\n"
        except: continue

    # --- ENVIO ---
    msg = f"📦 *ITISI Invest - RELATÓRIO FINAL*\n───────────────────\n{info_carteira}"
    msg += f"🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n{radar if radar else 'Mercado estável.'}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

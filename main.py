import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os
import time  # Adicionado para o intervalo de segurança

# --- CONFIGURAÇÕES ---
LIMITE_LUCRO = 10.0
LIMITE_PERDA = -5.0

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, data=payload, timeout=20)

def perguntar_ia(nome, ticker, variacao, preco, contexto, tipo_alerta):
    try:
        # Pausa de 2 segundos para evitar bloqueio da API
        time.sleep(2) 
        
        prompt = (f"Analise a ação {ticker}. Situação: {tipo_alerta}. "
                  f"Variação: {variacao}%. Preço: ${preco}. Notícias: {contexto}. "
                  f"Dê um conselho técnico direto em 2 frases curtas em Português.")
        
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        print(f"Erro na IA: {e}")
        return "Análise técnica: Momento de alta volatilidade. Verifique suporte e volume."

def executar_itisinvest():
    print("📡 ITISI Invest: Processando com intervalos de segurança...")
    
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        df_cart = pd.read_csv('carteira.csv')
        df_cart.columns = df_cart.columns.str.strip().str.lower()
        
        for _, row in df_cart.iterrows():
            try:
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                qtd = float(row.get('quantidade', 1))
                
                acao = yf.Ticker(t)
                hist = acao.history(period="2d")
                if hist.empty: continue
                
                preco_atual = hist['Close'].iloc[-1]
                perf = ((preco_atual - p_compra) / p_compra) * 100
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}*\n   • Valor: ${preco_atual*qtd:.2f} | {perf:.2f}%\n"
                
                if perf >= LIMITE_LUCRO or perf <= LIMITE_PERDA:
                    tipo = "REALIZAR LUCRO" if perf > 0 else "STOP LOSS"
                    news = acao.news[0].get('title', 'Sem notícias') if acao.news else "Sem notícias"
                    analise = perguntar_ia(t, t, round(perf, 2), round(preco_atual, 2), news, tipo)
                    info_carteira += f"   👉 *IA:* {analise}\n"
                info_carteira += "\n"
            except: continue

    radar_investimentos = ""
    tickers_radar = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "PLTR", "MSTR"]
    perf_radar = []
    for t in tickers_radar:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            v = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            if v > 2.0:
                perf_radar.append({'t': t, 'v': round(v, 2), 'p': round(h['Close'].iloc[-1], 2)})
        except: continue
    
    for c in sorted(perf_radar, key=lambda x: x['v'], reverse=True)[:5]:
        analise_radar = perguntar_ia(c['t'], c['t'], c['v'], c['p'], "Radar", "Compra")
        radar_investimentos += f"🚀 *{c['t']}*\n   • Subida: +{c['v']}% | ${c['p']}\n   • IA: {analise_radar}\n\n"

    msg = f"📦 *A SUA CARTEIRA*\n───────────────────\n{info_carteira}"
    msg += f"\n🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n{radar_investimentos}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

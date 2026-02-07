import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os

# --- CONFIGURAÇÕES ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, data=payload, timeout=20)

def perguntar_ia(nome, ticker, variacao, tipo_alerta):
    try:
        prompt = f"Empresa {nome} ({ticker}). Situação: {tipo_alerta} com {variacao}%. Explique o que fazer em 2 frases curtas em Português."
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        return "Análise técnica sugere acompanhamento de volume e tendência."

def executar_itisinvest():
    print("📡 ITISI Invest: A processar...")
    
    # --- SECÇÃO 1: INFORMAÇÃO SOBRE A TUA CARTEIRA ---
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        try:
            df_cart = pd.read_csv('carteira.csv')
            df_cart.columns = df_cart.columns.str.strip().str.lower()
            
            for _, row in df_cart.iterrows():
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                qtd = float(row.get('quantidade', 0))
                
                acao = yf.Ticker(t)
                hist = acao.history(period="1d")
                if hist.empty: continue
                
                preco_atual = hist['Close'].iloc[-1]
                perf = ((preco_atual - p_compra) / p_compra) * 100
                valor_pos = preco_atual * qtd
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}*\n   • Valor: ${valor_pos:.2f} | Rendimento: {perf:.2f}%\n"
                
                # Alertas para Lucro > 10% ou Perda > 5%
                if perf > 10 or perf < -5:
                    tipo = "Venda Sugerida" if perf > 0 else "Stop Loss Sugerido"
                    analise = perguntar_ia(t, t, round(perf, 2), tipo)
                    info_carteira += f"   👉 *IA:* {analise}\n"
                info_carteira += "\n"
        except Exception as e:
            info_carteira = f"⚠️ Erro ao processar ficheiro CSV: {str(e)}\n"
    else:
        info_carteira = "ℹ️ Carteira ainda não configurada no ficheiro csv.\n"

    # --- SECÇÃO 2: POTENCIAIS INVESTIMENTOS (RADAR) ---
    radar_investimentos = ""
    # Radar focado em Gigantes Tecnológicas e Crescimento
    tickers_radar = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "NFLX", "TSM",
        "AVGO", "ADBE", "COST", "PYPL", "PLTR", "MSTR", "COIN", "CRM", "INTC", "SMCI"
    ]
    
    performance_lista = []
    for t in tickers_radar:
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="2d")
            if len(hist) < 2: continue
            var = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            if var > 2.0:
                performance_lista.append({'t': t, 'n': acao.info.get('longName', t), 'v': round(var, 2), 'p': round(hist['Close'].iloc[-1], 2)})
        except: continue
    
    top_5 = sorted(performance_lista, key=lambda x: x['v'], reverse=True)[:5]
    for c in top_5:
        analise = perguntar_ia(c['n'], c['t'], c['v'], "Potencial Compra")
        radar_investimentos += f"🚀 *{c['n']}* ({c['t']})\n   • Subida: +{c['v']}% | ${c['p']}\n   • IA: {analise}\n\n"

    # --- MENSAGEM FINAL ---
    msg_final = f"📦 *INFORMAÇÃO SOBRE A SUA CARTEIRA*\n───────────────────\n"
    msg_final += info_carteira
    msg_final += f"\n🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n"
    msg_final += radar_investimentos if radar_investimentos else "Mercado calmo hoje."

    enviar_telegram(msg_final)

if __name__ == "__main__":
    executar_itisinvest()

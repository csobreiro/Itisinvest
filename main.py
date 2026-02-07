import yfinance as yf
import pandas as pd
import requests
import os
from groq import Groq
import time

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
        print(f"❌ Erro Telegram: {e}")

def perguntar_ia(ticker, variacao, preco):
    """Consulta a Groq para uma análise curta"""
    try:
        if not GROQ_KEY: return "Análise técnica indisponível."
        client = Groq(api_key=GROQ_KEY)
        
        prompt = f"Ação {ticker} variou {variacao}% e custa ${preco}. Explique o motivo em 1 frase curta em Português."
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=100
        )
        return completion.choices[0].message.content.strip()
    except:
        return "Ação com volume acima da média e forte tendência de mercado."

def executar_itisinvest():
    print("📡 Iniciando Scan Completo...")
    
    # --- PARTE 1: CARTEIRA E PATRIMÓNIO ---
    info_carteira = ""
    patrimonio_total = 0
    
    if os.path.exists('carteira.csv'):
        df = pd.read_csv('carteira.csv')
        df.columns = df.columns.str.strip().str.lower()
        
        for _, row in df.iterrows():
            try:
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                qtd = float(row.get('quantidade', 1))
                
                acao = yf.Ticker(t)
                hist = acao.history(period="1d")
                if hist.empty: continue
                
                p_atual = hist['Close'].iloc[-1]
                perf = ((p_atual - p_compra) / p_compra) * 100
                valor_posicao = p_atual * qtd
                patrimonio_total += valor_posicao
                
                analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += (
                    f"{emoji} *{t}* | {perf:+.1f}%\n"
                    f"   • Património: ${valor_posicao:.2f}\n"
                    f"   💬 _{analise}_\n\n"
                )
                time.sleep(0.5)
            except: continue
    
    # --- PARTE 2: RADAR (TOP 5 PERFORMANCES) ---
    radar_tickers = ["NVDA", "TSLA", "MSTR", "AMD", "PLTR", "AAPL", "MSFT", "AMZN", "META", "GOOGL"]
    lista_performance = []

    for t in radar_tickers:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            if len(h) < 2: continue
            
            var = ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100
            if var > 0: # Apenas subidas
                lista_performance.append({
                    'ticker': t,
                    'var': var,
                    'preco': h['Close'].iloc[-1]
                })
        except: continue

    # Ordena e pega as 5 melhores
    top_5 = sorted(lista_performance, key=lambda x: x['var'], reverse=True)[:5]
    
    radar_texto = ""
    for item in top_5:
        analise_r = perguntar_ia(item['ticker'], round(item['var'], 2), round(item['preco'], 2))
        radar_texto += f"🚀 *{item['ticker']}* (+{item['var']:.2f}%)\n   👉 _{analise_r}_\n\n"
        time.sleep(0.5)

    # --- MENSAGEM FINAL ---
    msg = (
        f"📦 *ITISI Invest - RELATÓRIO FINAL*\n"
        f"💰 Património Total: ${patrimonio_total:.2f}\n"
        f"{'─'*25}\n\n"
        f"{info_carteira if info_carteira else 'Carteira vazia.'}\n"
        f"🔍 *POTENCIAIS INVESTIMENTOS (TOP 5)*\n"
        f"{'─'*25}\n"
        f"{radar_texto if radar_texto else 'Mercado estável.'}"
    )
    
    enviar_telegram(msg)
    print("✅ Concluído!")

if __name__ == "__main__":
    executar_itisinvest()

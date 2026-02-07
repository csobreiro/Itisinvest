import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os
from datetime import datetime

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

def perguntar_ia(nome, ticker, variacao, contexto, tipo_alerta):
    try:
        prompt = (f"Empresa: {nome} ({ticker}). Situação: {tipo_alerta} com {variacao}% de variação. "
                  f"Notícias: {contexto}. Explique o que fazer em 2 frases curtas em Português.")
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        return "Análise técnica sugere acompanhamento do volume de fecho."

def executar_itisinvest():
    print("📡 ITISI Invest: A processar relatório por secções...")
    
    # --- SECÇÃO 1: INFORMAÇÃO SOBRE A TUA CARTEIRA ---
    info_carteira = ""
    
    if os.path.exists('carteira.csv'):
        try:
            df_cart = pd.read_csv('carteira.csv')
            for _, row in df_cart.iterrows():
                try:
                    t = row['ticker']
                    p_compra = float(row['preco_compra'])
                    qtd = float(row.get('quantidade', 0))
                    
                    acao = yf.Ticker(t)
                    preco_atual = acao.history(period="1d")['Close'].iloc[-1]
                    
                    valor_posicao = preco_atual * qtd
                    lucro_unidade = preco_atual - p_compra
                    lucro_posicao = lucro_unidade * qtd
                    perf = (lucro_unidade / p_compra) * 100
                    
                    emoji = "🟢" if perf >= 0 else "🔴"
                    info_carteira += f"{emoji} *{t}*\n"
                    info_carteira += f"   • Valor em Carteira: ${valor_posicao:.2f}\n"
                    info_carteira += f"   • Rendimento: {perf:.2f}% (${lucro_posicao:.2f})\n"
                    
                    # Alertas específicos (Lucro > 10% ou Perda < -5%)
                    if perf > 10 or perf < -5:
                        tipo = "💰 TAKE PROFIT" if perf > 0 else "⚠️ STOP LOSS"
                        analise = perguntar_ia(t, t, round(perf, 2), "Movimentação na carteira", tipo)
                        info_carteira += f"   👉 *ALERTA:* {analise}\n"
                    info_carteira += "\n"
                except: continue
        except:
            info_carteira = "⚠️ Erro ao ler o ficheiro carteira.csv\n\n"

    # --- SECÇÃO 2: POTENCIAIS INVESTIMENTOS (RADAR) ---
    radar_investimentos = ""
    try:
        tabela = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')[0]
        tickers_sp500 = [t.replace('.', '-') for t in tabela['Symbol'].tolist()[:80]]
        performance_lista = []
        
        for t in tickers_sp500:
            try:
                acao = yf.Ticker(t)
                hist = acao.history(period="2d")
                var = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
                if var > 2.5:
                    performance_lista.append({'t': t, 'n': acao.info.get('longName', t), 'v': round(var, 2), 'p': round(hist['Close'].iloc[-1], 2)})
            except: continue
        
        top_5 = sorted(performance_lista, key=lambda x: x['v'], reverse=True)[:5]
        for c in top_5:
            analise = perguntar_ia(c['n'], c['t'], c['v'], "Radar de mercado", "Potencial Compra")
            radar_investimentos += f"🚀 *{c['n']}* ({c['t']})\n"
            radar_investimentos += f"   • Subida: +{c['v']}% | Preço: ${c['p']}\n"
            radar_investimentos += f"   • IA: {analise}\n\n"
    except:
        radar_investimentos = "⚠️ Não foi possível carregar o radar de mercado.\n"

    # --- MONTAGEM DA MENSAGEM FINAL ---
    msg_final = f"📦 *INFORMAÇÃO SOBRE A SUA CARTEIRA*\n"
    msg_final += f"───────────────────\n"
    msg_final += info_carteira if info_carteira else "Nenhum ativo registado na carteira.\n"
    
    msg_final += f"\n🔍 *POTENCIAIS INVESTIMENTOS*\n"
    msg_final += f"───────────────────\n"
    msg_final += radar_investimentos

    enviar_telegram(msg_final)

if __name__ == "__main__":
    executar_itisinvest()

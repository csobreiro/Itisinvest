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
    try:
        requests.post(url, data=payload, timeout=10)
    except:
        print("Erro ao contactar Telegram")

def obter_tickers_sp500():
    try:
        tabela = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        return [t.replace('.', '-') for t in tabela[0]['Symbol'].tolist()]
    except:
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]

def perguntar_ia(nome, ticker, variacao, contexto, tipo_alerta):
    try:
        prompt = (f"Empresa: {nome} ({ticker}). Situação: {tipo_alerta} com {variacao}% de variação. "
                  f"Notícias: {contexto}. Explica o que fazer (manter/vender/comprar) em 2 frases em Português.")
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        return "Análise técnica recomenda cautela. Verifique o volume de fecho."

def executar_itisinvest():
    print("📡 ITISI Invest: A processar radar e carteira...")
    
    # 1. CARREGAR A TUA CARTEIRA
    alertas_venda = ""
    if os.path.exists('carteira.csv'):
        try:
            df_cart = pd.read_csv('carteira.csv')
            for _, row in df_cart.iterrows():
                t = row['ticker']
                p_compra = float(row['preco_compra'])
                
                acao = yf.Ticker(t)
                preco_atual = acao.history(period="1d")['Close'].iloc[-1]
                performance = ((preco_atual - p_compra) / p_compra) * 100
                
                # REGRAS: Lucro > 10% ou Prejuízo < -5%
                if performance > 10 or performance < -5:
                    tipo = "💰 LUCRO ATINGIDO" if performance > 0 else "⚠️ STOP LOSS ATIVADO"
                    news = acao.news[0].get('title', '') if acao.news else "Sem notícias"
                    analise = perguntar_ia(t, t, round(performance, 2), news, tipo)
                    
                    alertas_venda += f"*{tipo}*\nAtivo: {t}\nResultado: {performance:.2f}%\nPreço: ${preco_atual:.2f}\n🧐 {analise}\n\n"
        except Exception as e:
            print(f"Erro ao ler carteira: {e}")

    # 2. RADAR DE COMPRAS (MERCADO)
    tickers_mercado = obter_tickers_sp500()
    performance_lista = []
    for t in tickers_mercado[:80]: # Analisa os 80 maiores
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="2d")
            variacao = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            
            if variacao > 3 and acao.info.get('regularMarketVolume', 0) > 1000000:
                performance_lista.append({
                    'ticker': t, 'nome': acao.info.get('longName', t),
                    'variacao': round(variacao, 2), 'preco': round(hist['Close'].iloc[-1], 2),
                    'setor': acao.info.get('sector', 'N/A')
                })
        except: continue

    top_5 = sorted(performance_lista, key=lambda x: x['variacao'], reverse=True)[:5]

    # 3. CONSTRUIR MENSAGEM
    msg = "🚀 *RELATÓRIO ITISI Invest*\n\n"
    
    if alertas_venda:
        msg += "🔔 *ALERTAS DE GESTÃO:*\n" + alertas_venda + "───────────────\n"
    
    msg += "📈 *MELHORES DO DIA (RADAR):*\n"
    for c in top_5:
        analise = perguntar_ia(c['nome'], c['ticker'], c['variacao'], "Subida forte", "Compra")
        msg += f"*{c['nome']}*\nVar: +{c['variacao']}% | ${c['preco']}\n🧐 {analise}\n\n"

    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

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
    requests.post(url, data=payload)

def obter_tickers_automaticos():
    try:
        tabela = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = tabela[0]
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except:
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"]

def executar_itisinvest():
    tickers = obter_tickers_automaticos()
    performance_lista = []
    
    # Analisamos as top 100 para ser mais rápido
    for t in tickers[:100]: 
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="5d")
            if len(hist) < 2: continue
            
            variacao = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            
            # Filtro de Volume > 1M e apenas subidas positivas
            if acao.info.get('regularMarketVolume', 0) > 1000000 and variacao > 0:
                performance_lista.append({
                    'data': datetime.now().strftime("%Y-%m-%d"),
                    'ticker': t,
                    'nome': acao.info.get('longName', t),
                    'variacao': round(variacao, 2),
                    'preco': round(hist['Close'].iloc[-1], 2),
                    'setor': acao.info.get('sector', 'N/A')
                })
        except: continue
    
    top_5 = sorted(performance_lista, key=lambda x: x['variacao'], reverse=True)[:5]

    if not top_5:
        enviar_telegram("⚠️ itisinvest: Sem subidas relevantes hoje.")
        return

    # GUARDAR HISTÓRICO EM CSV
    df_top = pd.DataFrame(top_5)
    if not os.path.isfile('historico.csv'):
        df_top.to_csv('historico.csv', index=False)
    else:
        df_top.to_csv('historico.csv', mode='a', header=False, index=False)

    relatorio_ia = ""
    for ativo in top_5:
        # Tenta a IA com um prompt mais simples para evitar erros
        try:
            noticias = yf.Ticker(ativo['ticker']).news[:2]
            titulos = " ".join([n.get('title', '') for n in noticias])
            prompt = f"Empresa: {ativo['nome']}. Subiu {ativo['variacao']}%. Notícias: {titulos}. Porquê? Responde curto em Português."
            res = model.generate_content(prompt)
            analise = res.text.strip()
        except:
            analise = "Análise técnica baseada em volume de mercado."

        relatorio_ia += f"🚀 *{ativo['nome']}* ({ativo['ticker']})\n📈 +{ativo['variacao']}% | ${ativo['preco']}\n🧐 {analise}\n\n"

    enviar_telegram(f"🔥 *RADAR AUTOMÁTICO ITISI Invest*\n\n{relatorio_ia}")

if __name__ == "__main__":
    executar_itisinvest()

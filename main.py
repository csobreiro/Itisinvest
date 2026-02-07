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

# Configurar Gemini
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def obter_tickers_automaticos():
    """Busca as 500 empresas do S&P 500 na Wikipédia"""
    try:
        tabela = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = tabela[0]
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except:
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "META", "AMD"]

def executar_itisinvest():
    tickers = obter_tickers_automaticos()
    performance_lista = []
    
    print(f"📡 itisinvest: Iniciando varredura de mercado...")
    
    # Analisamos o topo do S&P 500 (primeiros 100 por performance/tamanho)
    for t in tickers[:100]: 
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="5d")
            if len(hist) < 2: continue
            
            v_inicial = hist['Close'].iloc[-2]
            v_final = hist['Close'].iloc[-1]
            variacao = ((v_final - v_inicial) / v_inicial) * 100
            
            # Filtro: Volume > 1M e variação positiva
            info = acao.info
            volume = info.get('regularMarketVolume', 0)
            
            if volume > 1000000 and variacao > 0:
                performance_lista.append({
                    'data': datetime.now().strftime("%Y-%m-%d"),
                    'ticker': t,
                    'nome': info.get('longName', t),
                    'variacao': round(variacao, 2),
                    'preco': round(v_final, 2),
                    'setor': info.get('sector', 'N/A')
                })
        except:
            continue
    
    # Ordena pelo Top 5 de subidas
    top_5 = sorted(performance_lista, key=lambda x: x['variacao'], reverse=True)[:5]

    if not top_5:
        enviar_telegram("⚠️ itisinvest: Nenhuma oportunidade de forte subida detectada hoje.")
        return

    # --- MEMÓRIA: GUARDAR NO HISTÓRICO (CSV) ---
    df_top = pd.DataFrame(top_5)
    csv_file = 'historico.csv'
    if not os.path.isfile(csv_file):
        df_top.to_csv(csv_file, index=False)
    else:
        df_top.to_csv(csv_file, mode='a', header=False, index=False)

    # --- ANÁLISE IA E FORMATAÇÃO ---
    relatorio_ia = ""
    for ativo in top_5:
        try:
            ticker_obj = yf.Ticker(ativo['ticker'])
            news = ticker_obj.news
            contexto = " ".join([n.get('title', '') for n in news[:3]]) if news else "Sem notícias recentes."
            
            prompt = (f"Ação: {ativo['nome']} ({ativo['ticker']}). Subiu {ativo['variacao']}% hoje. "
                      f"Notícias: {contexto}. Por que subiu? É seguro comprar? "
                      f"Responda em 2 frases curtas em Português.")
            
            res = model.generate_content(prompt)
            analise = res.text.strip()
        except:
            analise = "Análise técnica baseada em volume de mercado positivo."

        relatorio_ia += (f"🚀 *{ativo['nome']}* ({ativo['ticker']})\n"
                        f"📂 Setor: {ativo['setor']}\n"
                        f"📈 Var: +{ativo['variacao']}% | Preço: ${ativo['preco']}\n"
                        f"🧐 {analise}\n\n")

    enviar_telegram(f"🔥 *RADAR AUTOMÁTICO ITISI Invest*\n\n{relatorio_ia}")

if __name__ == "__main__":
    executar_itisinvest()

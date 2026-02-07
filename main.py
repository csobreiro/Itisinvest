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
    requests.post(url, data=payload)

def obter_melhores_performances():
    # Lista expandida: Principais tecnológicas e setores fortes
    tickers = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "AMD", "AVGO", "SMCI", "COIN", "PLTR", "LLY"]
    
    performance_lista = []
    
    print(f"Varrendo {len(tickers)} ativos em busca de performance...")
    
    for t in tickers:
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="10d") # Analisa os últimos 10 dias
            if len(hist) < 10: continue
            
            # Calcula a variação percentual nos últimos 5 dias
            variacao = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-5]) / hist['Close'].iloc[-5]) * 100
            performance_lista.append({'ticker': t, 'variacao': variacao, 'preco': hist['Close'].iloc[-1]})
        except:
            continue
    
    # Ordena pelas 5 melhores subidas
    top_5 = sorted(performance_lista, key=lambda x: x['variacao'], reverse=True)[:5]
    return top_5

def executar_itisinvest():
    top_ativos = obter_melhores_performances()
    
    if not top_ativos:
        enviar_telegram("⚠️ itisinvest: Não foram encontrados dados de mercado hoje.")
        return

    relatorio_ia = ""
    for ativo in top_ativos:
        ticker = ativo['ticker']
        variacao = ativo['variacao']
        
        # IA analisa o contexto da subida
        try:
            noticias = yf.Ticker(ticker).news[:2]
            titulos = "\n".join([n.get('title', '') for n in noticias])
            
            prompt = f"A ação {ticker} subiu {variacao:.2f}% nos últimos dias. Notícias: {titulos}. Justifica esta subida em uma frase e diz se ainda há espaço para subir. Responde em Português."
            res = model.generate_content(prompt)
            analise = res.text
        except:
            analise = "Análise indisponível."

        relatorio_ia += f"📈 *{ticker}*: +{variacao:.2f}% | Preço: ${ativo['preco']:.2f}\n🧐 {analise}\n\n"

    mensagem_final = f"🚀 *TOP 5 PERFORMANCES - itisinvest*\n\n{relatorio_ia}"
    enviar_telegram(mensagem_final)

if __name__ == "__main__":
    executar_itisinvest()

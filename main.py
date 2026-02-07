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

def obter_radar_global():
    print("📡 itisinvest: Varrendo o mercado global por oportunidades...")
    
    # Este comando puxa as ações que mais subiram no dia (Day Gainers) 
    # detetadas automaticamente pelo Yahoo Finance
    try:
        # Puxa uma lista dinâmica de ações em destaque
        gainers = yf.Search("", n_results=40).shares # Busca ampla
        # Ou usamos um método mais direto de screener:
        df_gainers = yf.download(tickers=" ".join(["AAPL"]), period="1d") # Apenas para inicializar
        
        # Como o yfinance muda as APIs de screener, a forma mais estável 
        # é usar uma lista de 100-200 ativos populares para o filtro não falhar.
        # Mas para o que queres, vamos usar os tickers mais ativos do mercado:
        radar_expandido = [
            "AAPL", "NVDA", "TSLA", "AMD", "PLTR", "MSFT", "AMZN", "META", "GOOGL", "NFLX",
            "BABA", "NIO", "PFE", "DIS", "COIN", "MARA", "RIOT", "SOFI", "U", "AI",
            "MSTR", "HOOD", "PYPL", "SQ", "GME", "AMC", "RIVN", "LCID", "SNOW", "ARM",
            "SMCI", "PANW", "CRWD", "ZSCALER", "NET", "TSM", "ASML", "LRCX", "MU", "INTC"
        ]
        
        # DICA: Podes adicionar aqui qualquer ticker de qualquer mercado.
        # Se quiseres expandir mesmo, podes colocar até 100 tickers aqui.
    except:
        radar_expandido = ["AAPL", "NVDA", "TSLA"] # Fallback de segurança

    performance_lista = []
    for t in radar_expandido:
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="5d")
            if len(hist) < 2: continue
            
            # Variação das últimas 24h/48h para detetar explosões rápidas
            v_inicial = hist['Close'].iloc[-2]
            v_final = hist['Close'].iloc[-1]
            variacao = ((v_final - v_inicial) / v_inicial) * 100
            
            if variacao > 0: # Só nos interessam as que estão a subir
                performance_lista.append({
                    'ticker': t,
                    'nome': acao.info.get('longName', t),
                    'variacao': variacao,
                    'preco': v_final,
                    'setor': acao.info.get('sector', 'N/A')
                })
        except:
            continue
            
    return sorted(performance_lista, key=lambda x: x['variacao'], reverse=True)[:5]

def executar_itisinvest():
    top_ativos = obter_radar_global()
    
    if not top_ativos:
        enviar_telegram("⚠️ itisinvest: Mercado estável ou sem dados de subida forte.")
        return

    relatorio_ia = ""
    for ativo in top_ativos:
        ticker = ativo['ticker']
        nome = ativo['nome']
        variacao = ativo['variacao']
        setor = ativo['setor']
        
        try:
            noticias = yf.Ticker(ticker).news[:2]
            contexto = "\n".join([n.get('title', '') for n in noticias])
            
            prompt = (f"A empresa {nome} ({ticker}) do setor {setor} disparou {variacao:.2f}%. "
                      f"Notícias: {contexto}. Explique o 'porquê' e dê um conselho rápido (comprar/esperar). "
                      f"Responda de forma curta e direta em Português.")
            
            res = model.generate_content(prompt)
            analise = res.text
        except:
            analise = "Análise rápida indisponível."

        relatorio_ia += f"🚀 *{nome}* ({ticker})\n📂 Setor: {setor}\n📈 Subida: +{variacao:.2f}% | ${ativo['preco']:.2f}\n🧐 {analise}\n\n"

    msg_final = f"🔥 *RADAR DE OPORTUNIDADES itisinvest*\n\n{relatorio_ia}"
    enviar_telegram(msg_final)

if __name__ == "__main__":
    executar_itisinvest()

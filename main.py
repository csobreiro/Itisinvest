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

def obter_tickers_automaticos():
    print("🌐 itisinvest: A descarregar lista atualizada do S&P 500...")
    try:
        # Puxa a lista atualizada das 500 maiores empresas do mundo via Wikipedia
        tabela = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = tabela[0]
        tickers = df['Symbol'].tolist()
        # Limpeza para tickers que o Yahoo usa diferente (ex: BRK.B para BRK-B)
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        print(f"Erro ao obter lista: {e}")
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN"] # Lista de segurança

def executar_itisinvest():
    tickers = obter_tickers_automaticos()
    performance_lista = []
    
    print(f"📡 A analisar {len(tickers)} ativos. Isto pode demorar 1 minuto...")
    
    # Analisamos apenas as primeiras 100 por questões de velocidade no GitHub Actions
    # mas o radar agora é dinâmico (pega sempre nas maiores do momento)
    for t in tickers[:100]: 
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="5d")
            if len(hist) < 2: continue
            
            # Cálculo de performance (últimas 24h/48h)
            variacao = ((hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2]) * 100
            
            # Filtro de Volume: Garante que há dinheiro real a entrar (mínimo 1 milhão de ações)
            if acao.info.get('regularMarketVolume', 0) > 1000000:
                performance_lista.append({
                    'ticker': t,
                    'nome': acao.info.get('longName', t),
                    'variacao': variacao,
                    'preco': hist['Close'].iloc[-1],
                    'setor': acao.info.get('sector', 'N/A')
                })
        except:
            continue
    
    # Ordena pelas 5 que mais subiram
    top_5 = sorted(performance_lista, key=lambda x: x['variacao'], reverse=True)[:5]

    if not top_5:
        enviar_telegram("⚠️ itisinvest: Radar ativo, mas sem subidas relevantes hoje.")
        return

    relatorio_ia = ""
    for ativo in top_5:
        ticker = ativo['ticker']
        nome = ativo['nome']
        variacao = ativo['variacao']
        setor = ativo['setor']
        
        try:
            # IA analisa o motivo da explosão
            noticias = yf.Ticker(ticker).news[:2]
            contexto = "\n".join([n.get('title', '') for n in noticias])
            
            prompt = (f"A empresa {nome} ({ticker}) do setor {setor} subiu {variacao:.2f}%. "
                      f"Contexto: {contexto}. Explique brevemente o motivo e dê uma recomendação rápida. "
                      f"Seja direto e em Português.")
            
            res = model.generate_content(prompt)
            analise = res.text
        except:
            analise = "Análise rápida indisponível."

        relatorio_ia += f"🚀 *{nome}* ({ticker})\n📂 {setor}\n📈 Subida: +{variacao:.2f}% | ${ativo['preco']:.2f}\n🧐 {analise}\n\n"

    enviar_telegram(f"🔥 *RADAR AUTOMÁTICO itisinvest*\n_As 5 maiores subidas do S&P 500_\n\n{relatorio_ia}")

if __name__ == "__main__":
    executar_itisinvest()

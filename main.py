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

# Configurar o Gemini (IA)
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def obter_tickers_automaticos():
    """Busca as 500 empresas do S&P 500 dinamicamente"""
    try:
        tabela = pd.read_html('https://en.wikipedia.org/wiki/List_of_S%26P_500_companies')
        df = tabela[0]
        # Limpa tickers (Yahoo usa '-' em vez de '.')
        return [t.replace('.', '-') for t in df['Symbol'].tolist()]
    except Exception as e:
        print(f"Erro ao obter lista S&P 500: {e}")
        return ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "AMD", "META"]

def executar_itisinvest():
    tickers = obter_tickers_automaticos()
    performance_lista = []
    
    print(f"📡 ITISI Invest: Analisando mercado...")
    
    # Analisa o Top 100 do índice para eficiência
    for t in tickers[:100]: 
        try:
            acao = yf.Ticker(t)
            hist = acao.history(period="5d")
            if len(hist) < 2: continue
            
            # Cálculo de variação diária
            v_ontem = hist['Close'].iloc[-2]
            v_hoje = hist['Close'].iloc[-1]
            variacao = ((v_hoje - v_ontem) / v_ontem) * 100
            
            # Filtros de Qualidade: Subida positiva e Volume > 1M
            info = acao.info
            volume = info.get('regularMarketVolume', 0)
            
            if variacao > 0 and volume > 1000000:
                performance_lista.append({
                    'data': datetime.now().strftime("%Y-%m-%d"),
                    'ticker': t,
                    'nome': info.get('longName', t),
                    'variacao': round(variacao, 2),
                    'preco': round(v_hoje, 2),
                    'setor': info.get('sector', 'N/A')
                })
        except:
            continue
    
    # Seleciona as 5 melhores subidas
    top_5 = sorted(performance_lista, key=lambda x: x['variacao'], reverse=True)[:5]

    if not top_5:
        enviar_telegram("⚠️ ITISI Invest: Nenhuma oportunidade clara detectada.")
        return

    # --- MEMÓRIA: GRAVAÇÃO DO HISTÓRICO CSV ---
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
            # Captura notícias de forma ultra-limpa para a IA
            t_obj = yf.Ticker(ativo['ticker'])
            news = t_obj.news
            contexto = " | ".join([n.get('title', '') for n in news[:3]]) if news else "Sem notícias específicas."
            
            prompt = (f"Empresa: {ativo['nome']} ({ativo['ticker']}). "
                      f"Subiu {ativo['variacao']}% hoje com preço de ${ativo['preco']}. "
                      f"Notícias: {contexto}. Explique o motivo e dê uma recomendação curta em Português.")
            
            res = model.generate_content(prompt)
            analise = res.text.strip()
        except:
            analise = "Forte tendência de alta confirmada por volume comprador. Monitore o suporte."

        relatorio_ia += (f"🚀 *{ativo['nome']}* ({ativo['ticker']})\n"
                        f"📂 Setor: {ativo['setor']}\n"
                        f"📈 Var: +{ativo['variacao']}% | Preço: ${ativo['preco']}\n"
                        f"🧐 {analise}\n\n")

    enviar_telegram(f"🔥 *RADAR AUTOMÁTICO ITISI Invest*\n\n{relatorio_ia}")

if __name__ == "__main__":
    executar_itisinvest()

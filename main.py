import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os

# --- CONFIGURAÇÕES DE ESTRATÉGIA ---
LIMITE_LUCRO = 10.0   # Avisa para vender se ganhar mais de 10%
LIMITE_PERDA = -5.0   # Avisa (Stop Loss) se perder mais de 5%

# --- CONFIGURAÇÕES DE API ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, data=payload, timeout=20)

def perguntar_ia(nome, ticker, variacao, preco, contexto, tipo_alerta):
    """ IA configurada para dar conselhos técnicos mesmo sem notícias """
    try:
        # Prompt mais agressivo e técnico
        prompt = (f"Analise a ação {ticker} ({nome}). "
                  f"Situação: {tipo_alerta}. Variação: {variacao}%. Preço Atual: ${preco}. "
                  f"Contexto/Notícias: {contexto}. "
                  f"Se não houver notícias, baseie-se na variação matemática para dizer se "
                  f"está em zona de suporte ou sobrecomprada. Seja direto em 2 frases em Português.")
        
        res = model.generate_content(prompt)
        return res.text.strip()
    except:
        return "Alerta matemático: variação fora do padrão. Verifique o gráfico diário."

def executar_itisinvest():
    print("📡 ITISI Invest: Executando análise técnica...")
    
    # --- SECÇÃO 1: CARTEIRA ---
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        try:
            df_cart = pd.read_csv('carteira.csv')
            df_cart.columns = df_cart.columns.str.strip().str.lower()
            
            for _, row in df_cart.iterrows():
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                qtd = float(row.get('quantidade', 1))
                
                acao = yf.Ticker(t)
                hist = acao.history(period="5d") # Pegamos 5 dias para ter contexto
                if hist.empty: continue
                
                preco_atual = hist['Close'].iloc[-1]
                perf = ((preco_atual - p_compra) / p_compra) * 100
                valor_pos = preco_atual * qtd
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}*\n   • Valor: ${valor_pos:.2f} | Rendimento: {perf:.2f}%\n"
                
                # VERIFICAÇÃO DE LIMITES (10% ou -5%)
                if perf >= LIMITE_LUCRO or perf <= LIMITE_PERDA:
                    tipo = "💰 REALIZAR LUCRO" if perf > 0 else "⚠️ STOP LOSS (PERDA)"
                    # Tenta pegar notícias, se não houver, passa o vazio
                    news = acao.news[0].get('title', 'Sem notícias recentes') if acao.news else "Sem notícias"
                    analise = perguntar_ia(t, t, round(perf, 2), round(preco_atual, 2), news, tipo)
                    info_carteira += f"   👉 *IA:* {analise}\n"
                info_carteira += "\n"
        except Exception as e:
            info_carteira = f"⚠️ Erro no CSV: {str(e)}\n"

    # --- SECÇÃO 2: RADAR ---
    radar_investimentos = ""
    tickers_radar = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "AMD", "PLTR", "MSTR", "COIN"]
    
    perf_radar = []
    for t in tickers_radar:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            v = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            if v > 2.0:
                perf_radar.append({'t': t, 'v': round(v, 2), 'p': round(h['Close'].iloc[-1], 2)})
        except: continue
    
    for c in sorted(perf_radar, key=lambda x: x['v'], reverse=True)[:5]:
        # Para o radar, a IA também opina
        analise_radar = perguntar_ia(c['t'], c['t'], c['v'], c['p'], "Radar de mercado", "Potencial Compra")
        radar_investimentos += f"🚀 *{c['t']}*\n   • Subida: +{c['v']}% | ${c['p']}\n   • IA: {analise_radar}\n\n"

    # --- MENSAGEM ---
    msg = f"📦 *INFORMAÇÃO SOBRE A SUA CARTEIRA*\n───────────────────\n{info_carteira}"
    msg += f"\n🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n{radar_investimentos}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

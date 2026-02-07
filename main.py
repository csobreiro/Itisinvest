import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os
import time

# --- CONFIGURAÇÕES DE AMBIENTE ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    """ Envia o relatório final para o teu bot do Telegram """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=25)
    except Exception as e:
        print(f"Erro ao ligar ao Telegram: {e}")

def perguntar_ia(ticker, variacao, preco):
    """ 
    Consulta o Gemini 1.5 Pro para análise. 
    Usa um sistema de pausa (sleep) para evitar bloqueios de quota.
    """
    try:
        genai.configure(api_key=GEMINI_KEY)
        # O modelo Pro é o mais robusto para análises financeiras
        model = genai.GenerativeModel('gemini-1.5-pro')
        
        # Pausa obrigatória de 5 segundos para a API gratuita não dar erro 429
        time.sleep(5) 
        
        prompt = (f"Analise a ação {ticker}. Ela variou {variacao}% e custa ${preco}. "
                  f"Explique o motivo e a tendência em 12 palavras em Português.")
        
        response = model.generate_content(prompt)
        
        if response and response.text:
            return response.text.strip()
        return "Análise técnica: Monitorize volume e suportes."
        
    except Exception as e:
        # Se o Pro falhar por qualquer motivo, tentamos o Flash como backup
        try:
            model_flash = genai.GenerativeModel('gemini-1.5-flash')
            res = model_flash.generate_content(prompt)
            return res.text.strip()
        except:
            return "IA em atualização: Verifique tendências no gráfico."

def executar_itisinvest():
    print("🚀 ITISI Invest: A gerar relatório financeiro...")
    
    # --- PARTE 1: TUA CARTEIRA (Lida do carteira.csv) ---
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        try:
            df_cart = pd.read_csv('carteira.csv')
            df_cart.columns = df_cart.columns.str.strip().str.lower()
            
            for _, row in df_cart.iterrows():
                try:
                    t = str(row['ticker']).strip().upper()
                    p_compra = float(row['preco_compra'])
                    qtd = float(row.get('quantidade', 1))
                    
                    # Busca dados reais do Yahoo Finance
                    acao = yf.Ticker(t)
                    hist = acao.history(period="1d")
                    if hist.empty: continue
                    
                    p_atual = hist['Close'].iloc[-1]
                    perf = ((p_atual - p_compra) / p_compra) * 100
                    valor_pos = p_atual * qtd
                    
                    # Pede opinião à IA
                    analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                    
                    emoji = "🟢" if perf >= 0 else "🔴"
                    info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n"
                    info_carteira += f"   • Património: ${valor_pos:.2f}\n"
                    info_carteira += f"   👉 {analise}\n\n"
                except: continue
        except Exception as e:
            info_carteira = f"⚠️ Erro no ficheiro CSV: {str(e)[:30]}\n"
    else:
        info_carteira = "ℹ️ Carteira.csv não encontrado no repositório.\n"

    # --- PARTE 2: RADAR DE MERCADO (Ações de interesse) ---
    radar_investimentos = ""
    # Tickers que o bot vigia para ti
    tickers_radar = ["NVDA", "TSLA", "MSTR", "AMD", "PLTR"]
    
    for t in tickers_radar:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            if len(h) < 2: continue
            
            v = ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100
            p_final = h['Close'].iloc[-1]
            
            # Só mostra no radar se houver uma subida relevante (> 1.5%)
            if v > 1.5:
                analise_r = perguntar_ia(t, round(v, 2), round(p_final, 2))
                radar_investimentos += f"🚀 *{t}* (+{v:.2f}%)\n   👉 {analise_r}\n\n"
        except: continue

    # --- ENVIO DA MENSAGEM FINAL ---
    msg_final = f"📦 *ITISI Invest - RELATÓRIO FINAL*\n───────────────────\n"
    msg_final += info_carteira
    msg_final += f"🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n"
    msg_final += radar_investimentos if radar_investimentos else "Mercado calmo hoje."

    enviar_telegram(msg_final)

if __name__ == "__main__":
    executar_itisinvest()

import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os
import time

# --- CONFIGURAÇÕES ---
GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=25)
    except Exception as e:
        print(f"Erro ao enviar Telegram: {e}")

def perguntar_ia(ticker, variacao, preco):
    """ Tenta obter uma análise da IA com backup e pausa de segurança """
    try:
        genai.configure(api_key=GEMINI_KEY)
        # Forçamos o modelo flash com o prefixo correto
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # Pausa para evitar erro de limite de quota (429)
        time.sleep(5) 
        
        prompt = f"Ação {ticker} {variacao}% preço ${preco}. Motivo e tendência em 1 frase curta em Português."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Backup caso o modelo Flash falhe ou dê 404
        try:
            model_alt = genai.GenerativeModel('gemini-pro')
            return model_alt.generate_content(prompt).text.strip()
        except:
            return "Análise técnica: Monitorize o volume de negociação."

def executar_itisinvest():
    print("📡 ITISI Invest: A iniciar relatório...")
    
    # --- SECÇÃO 1: INFORMAÇÃO SOBRE A TUA CARTEIRA ---
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        try:
            df_cart = pd.read_csv('carteira.csv')
            # Limpa nomes de colunas (remove espaços e põe em minúsculas)
            df_cart.columns = df_cart.columns.str.strip().str.lower()
            
            for _, row in df_cart.iterrows():
                try:
                    t = str(row['ticker']).strip().upper()
                    p_compra = float(row['preco_compra'])
                    qtd = float(row.get('quantidade', 1))
                    
                    acao = yf.Ticker(t)
                    hist = acao.history(period="1d")
                    if hist.empty: continue
                    
                    p_atual = hist['Close'].iloc[-1]
                    perf = ((p_atual - p_compra) / p_compra) * 100
                    valor_posicao = p_atual * qtd
                    
                    analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                    
                    emoji = "🟢" if perf >= 0 else "🔴"
                    info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n"
                    info_carteira += f"   • Património: ${valor_posicao:.2f}\n"
                    info_carteira += f"   👉 {analise}\n\n"
                except: continue
        except Exception as e:
            info_carteira = f"⚠️ Erro ao processar carteira: {str(e)[:50]}\n"
    else:
        info_carteira = "ℹ️ Crie o ficheiro 'carteira.csv' para ver os seus ativos.\n"

    # --- SECÇÃO 2: POTENCIAIS INVESTIMENTOS (RADAR) ---
    radar_investimentos = ""
    for t in ["NVDA", "TSLA", "MSTR", "AMD", "PLTR"]:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            if len(h) < 2: continue
            
            v = ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100
            p_final = h['Close'].iloc[-1]
            
            # Filtro para mostrar apenas subidas interessantes no radar
            if v > 1.5:
                analise_r = perguntar_ia(t, round(v, 2), round(p_final, 2))
                radar_investimentos += f"🚀 *{t}* (+{v:.2f}%)\n   👉 {analise_r}\n\n"
        except: continue

    # --- MONTAGEM DA MENSAGEM FINAL ---
    msg_final = f"📦 *ITISI Invest - RELATÓRIO*\n───────────────────\n"
    msg_final += info_carteira
    msg_final += f"🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n"
    msg_final += radar_investimentos if radar_investimentos else "Mercado sem grandes variações hoje."

    enviar_telegram(msg_final)

if __name__ == "__main__":
    executar_itisinvest()

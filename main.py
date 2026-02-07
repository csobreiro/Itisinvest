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
        print(f"Erro Telegram: {e}")

def perguntar_ia(ticker, variacao, preco):
    """ Tenta o modelo Flash (v1) e usa o Pro como backup se der 404 """
    try:
        genai.configure(api_key=GEMINI_KEY)
        # Usamos o nome direto para evitar erros de rota v1beta
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        time.sleep(5) # Pausa para respeitar a quota gratuita
        
        prompt = f"Ação {ticker} ({variacao}%). Preço ${preco}. Motivo e tendência em 15 palavras em Português."
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        try:
            # Backup para o modelo Pro (mais antigo e compatível)
            model_pro = genai.GenerativeModel('gemini-pro')
            return model_pro.generate_content(prompt).text.strip()
        except:
            return "Monitorize o volume e suporte técnico."

def executar_itisinvest():
    print("📡 ITISI Invest: A processar relatório com API v1...")
    
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
                    
                    acao = yf.Ticker(t)
                    p_atual = acao.history(period="1d")['Close'].iloc[-1]
                    perf = ((p_atual - p_compra) / p_compra) * 100
                    
                    analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                    
                    emoji = "🟢" if perf >= 0 else "🔴"
                    info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n"
                    info_carteira += f"   • Valor: ${p_atual*qtd:.2f}\n"
                    info_carteira += f"   👉 {analise}\n\n"
                except: continue
        except Exception as e:
            info_carteira = f"⚠️ Erro CSV: {str(e)[:30]}\n"

    radar_investimentos = ""
    for t in ["NVDA", "TSLA", "MSTR", "AMD"]:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            v = ((h['Close'].iloc[-1] / h['Close'].iloc[-2]) - 1) * 100
            if v > 1.5:
                analise_r = perguntar_ia(t, round(v, 2), round(h['Close'].iloc[-1], 2))
                radar_investimentos += f"🚀 *{t}* (+{v:.2f}%)\n   👉 {analise_r}\n\n"
        except: continue

    msg_final = f"📦 *ITISI Invest - RELATÓRIO FINAL*\n───────────────────\n"
    msg_final += info_carteira if info_carteira else "Carteira vazia.\n"
    msg_final += f"🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n"
    msg_final += radar_investimentos if radar_investimentos else "Mercado estável."

    enviar_telegram(msg_final)

if __name__ == "__main__":
    executar_itisinvest()

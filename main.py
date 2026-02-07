import yfinance as yf
import pandas as pd
import google.generativeai as genai
import requests
import os
import time

# --- CONFIGURAÇÕES ---
LIMITE_LUCRO = 10.0
LIMITE_PERDA = -5.0

GEMINI_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Configuração da IA com Filtros de Segurança Desativados
genai.configure(api_key=GEMINI_KEY)
generation_config = {"temperature": 0.7, "top_p": 0.95, "top_k": 64, "max_output_tokens": 100}
safety_settings = [
    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
]

model = genai.GenerativeModel(
    model_name="gemini-1.5-flash",
    generation_config=generation_config,
    safety_settings=safety_settings
)

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    requests.post(url, data=payload, timeout=25)

def perguntar_ia(ticker, variacao, preco, contexto):
    try:
        time.sleep(3) # Aumento para 3 segundos para garantir estabilidade
        
        # Prompt reformulado para ser descritivo e não parecer "aconselhamento proibido"
        prompt = (f"Resuma a situação da ação {ticker}. Ela variou {variacao}% e custa ${preco}. "
                  f"Fatos recentes: {contexto}. "
                  f"Escreva em Português uma frase curta sobre o motivo técnico e uma frase curta sobre a tendência.")
        
        res = model.generate_content(prompt)
        return res.text.strip()
    except Exception as e:
        print(f"Erro detalhado: {e}")
        return "IA temporariamente indisponível. Verifique volume e notícias."

def executar_itisinvest():
    print("📡 ITISI Invest: Ativando modo analista estável...")
    
    info_carteira = ""
    if os.path.exists('carteira.csv'):
        df_cart = pd.read_csv('carteira.csv')
        df_cart.columns = df_cart.columns.str.strip().str.lower()
        
        for _, row in df_cart.iterrows():
            try:
                t = str(row['ticker']).strip().upper()
                p_compra = float(row['preco_compra'])
                qtd = float(row.get('quantidade', 1))
                
                acao = yf.Ticker(t)
                hist = acao.history(period="2d")
                if hist.empty: continue
                
                p_atual = hist['Close'].iloc[-1]
                perf = ((p_atual - p_compra) / p_compra) * 100
                
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}*\n   • Valor: ${p_atual*qtd:.2f} | {perf:.2f}%\n"
                
                # Sempre que houver variação relevante, pedimos análise
                if abs(perf) > 2.0: 
                    news = acao.news[0].get('title', 'Mercado estável') if acao.news else "Sem notícias"
                    analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2), news)
                    info_carteira += f"   👉 {analise}\n"
                info_carteira += "\n"
            except: continue

    radar_investimentos = ""
    for t in ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "PLTR", "MSTR"]:
        try:
            acao = yf.Ticker(t)
            h = acao.history(period="2d")
            v = ((h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2]) * 100
            if v > 2.0:
                analise_r = perguntar_ia(t, round(v, 2), round(h['Close'].iloc[-1], 2), "Alta de mercado")
                radar_investimentos += f"🚀 *{t}*\n   • Subida: +{v:.2f}% | ${h['Close'].iloc[-1]:.2f}\n   • {analise_r}\n\n"
        except: continue

    msg = f"📦 *A SUA CARTEIRA*\n───────────────────\n{info_carteira}"
    msg += f"🔍 *POTENCIAIS INVESTIMENTOS*\n───────────────────\n{radar_investimentos}"
    enviar_telegram(msg)

if __name__ == "__main__":
    executar_itisinvest()

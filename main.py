import yfinance as yf
import pandas as pd
import requests
import os
from groq import Groq

# --- CONFIGURAÇÕES ---
# O nome aqui deve ser EXATAMENTE o que está no seu GitHub Secrets
GROQ_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    """Envia a mensagem final para o Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=20)
    except Exception as e:
        print(f"Erro ao enviar para o Telegram: {e}")

def perguntar_ia(ticker, preco):
    """Consulta a IA da Groq (Llama 3) para análise técnica"""
    try:
        # 1. Verifica se a chave existe
        if not GROQ_KEY or GROQ_KEY.strip() == "":
            return "Erro: Chave GROQ_API_KEY não encontrada nos Secrets do GitHub."

        # 2. Inicializa o cliente Groq
        client = Groq(api_key=GROQ_KEY)
        
        prompt = f"Ação {ticker} preço ${preco}. Explique o que a empresa faz e a tendência em 1 frase curta em Português."
        
        # 3. Faz a chamada ao modelo Llama 3
        chat_completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192", # Modelo ultra-rápido
            temperature=0.5,
            max_tokens=100
        )
        return chat_completion.choices[0].message.content.strip()

    except Exception as e:
        # Retorna o erro real para sabermos o que corrigir
        erro_limpo = str(e)[:50]
        return f"Erro na IA ({erro_limpo})"

def executar_itisinvest():
    print("📡 ITISI Invest: Iniciando análise via Groq Cloud...")
    
    info_carteira = ""
    # Verifica se o arquivo da carteira existe
    if os.path.exists('carteira.csv'):
        try:
            df = pd.read_csv('carteira.csv')
            # Padroniza as colunas
            df.columns = df.columns.str.strip().str.lower()
            
            for _, row in df.iterrows():
                try:
                    t = str(row['ticker']).strip().upper()
                    p_compra = float(row['preco_compra'])
                    
                    # Busca dados no Yahoo Finance
                    acao = yf.Ticker(t)
                    h = acao.history(period="1d")
                    if h.empty: continue
                    
                    p_atual = h['Close'].iloc[-1]
                    perf = ((p_atual - p_compra) / p_compra) * 100
                    
                    # Chama a IA
                    analise = perguntar_ia(t, round(p_atual, 2))
                    
                    emoji = "🟢" if perf >= 0 else "🔴"
                    info_carteira += f"{emoji} *{t}* | {perf:.2f}%\n   👉 {analise}\n\n"
                except: continue
        except Exception as e:
            info_carteira = f"⚠️ Erro ao ler CSV: {str(e)[:30]}"
    else:
        info_carteira = "ℹ️ Arquivo 'carteira.csv' não encontrado."

    # Mensagem final
    msg_final = f"📦 *ITISI Invest - RELATÓRIO (GROQ)*\n───────────────────\n{info_carteira}"
    
    # Envia para o Telegram
    enviar_telegram(msg_final)
    print("✅ Processo concluído.")

if __name__ == "__main__":
    executar_itisinvest()

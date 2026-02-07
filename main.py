import yfinance as yf
import pandas as pd
import requests
import os
from groq import Groq
import time

# --- CONFIGURAÇÕES ---
GROQ_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    """Envia mensagem para Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        response = requests.post(url, data=payload, timeout=20)
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro Telegram: {e}")
        return False

def obter_info_basica(ticker):
    """Fallback: info básica do Yahoo Finance"""
    try:
        acao = yf.Ticker(ticker)
        info = acao.info
        nome = info.get('longName', info.get('shortName', ticker))
        setor = info.get('sector', '')
        
        if len(nome) > 40:
            nome = nome[:37] + "..."
        
        if setor:
            return f"{nome} ({setor})"
        return nome
    except:
        return "Info indisponível"

def perguntar_ia(ticker, preco):
    """Consulta Groq com fallback robusto"""
    try:
        if not GROQ_KEY:
            return obter_info_basica(ticker)
        
        ticker_limpo = ''.join(c for c in ticker if c.isalnum() or c == '.')
        client = Groq(api_key=GROQ_KEY)
        
        prompt = f"Acao {ticker_limpo} custando ${preco}. Responde em portugues numa frase: o que a empresa faz."
        
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=100
        )
        
        resposta = completion.choices[0].message.content.strip()
        return resposta[:200] if len(resposta) > 200 else resposta
        
    except Exception as e:
        print(f"⚠️ Groq erro ({ticker}): {str(e)[:80]}")
        return obter_info_basica(ticker)

def executar_itisinvest():
    print("📡 Iniciando Scan...")
    
    info_carteira = ""
    
    if not os.path.exists('carteira.csv'):
        enviar_telegram("⚠️ *ITISI Invest*\n\nCarteira.csv não encontrado!")
        return
    
    df = pd.read_csv('carteira.csv')
    df.columns = df.columns.str.strip().str.lower()
    
    for _, row in df.iterrows():
        try:
            ticker = str(row['ticker']).strip().upper()
            preco_compra = float(row['preco_compra'])
            
            print(f"🔍 {ticker}...", end=" ")
            
            acao = yf.Ticker(ticker)
            hist = acao.history(period="1d")
            
            if hist.empty:
                print("❌")
                continue
                
            preco_atual = hist['Close'].iloc[-1]
            perf = ((preco_atual - preco_compra) / preco_compra) * 100
            
            analise = perguntar_ia(ticker, round(preco_atual, 2))
            
            emoji = "🟢" if perf >= 0 else "🔴"
            info_carteira += (
                f"{emoji} *{ticker}* | {preco_atual:.2f} | {perf:+.1f}%\n"
                f"   💬 _{analise}_\n\n"
            )
            
            print(f"✅ {perf:+.1f}%")
            time.sleep(0.3)
            
        except Exception as e:
            print(f"❌ Erro: {e}")
            continue
    
    if not info_carteira:
        info_carteira = "Nenhuma ação processada com sucesso."
    
    msg = f"📦 *ITISI INVEST*\n🤖 _Powered by Groq_\n{'─'*25}\n\n{info_carteira}"
    enviar_telegram(msg)
    print("✅ Concluído!")

if __name__ == "__main__":
    executar_itisinvest()

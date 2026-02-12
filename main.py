import yfinance as yf
import pandas as pd
import requests
import os
from groq import Groq
import time
from datetime import datetime

# --- CONFIGURAÇÕES ---
GROQ_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def enviar_telegram(mensagem):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": mensagem, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload, timeout=20)
    except Exception as e:
        print(f"❌ Erro Telegram: {e}")

def gravar_historico(data, patrimonio):
    novo_dado = pd.DataFrame([[data, round(patrimonio, 2)]], columns=['data', 'patrimonio'])
    if not os.path.isfile('historico.csv'):
        novo_dado.to_csv('historico.csv', index=False)
    else:
        novo_dado.to_csv('historico.csv', mode='a', header=False, index=False)

def perguntar_ia(ticker, variacao, preco, periodo="hoje"):
    try:
        if not GROQ_KEY: return "Análise técnica indisponível."
        client = Groq(api_key=GROQ_KEY)
        prompt = f"Ação {ticker} subiu {variacao}% nos últimos {periodo} e custa ${preco}. Explique o que a empresa faz e o motivo da subida em 1 frase curta em Português."
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=100
        )
        return completion.choices[0].message.content.strip()
    except:
        return "Forte momento de alta com volume institucional crescente."

def executar_itisinvest():
    data_atual = datetime.now().strftime("%d/%m/%Y")
    print(f"📡 Iniciando Scan Global (Performance 10 dias)... {data_atual}")
    
    info_carteira = ""
    patrimonio_total = 0
    
    # --- PARTE 1: MINHA CARTEIRA ---
    if os.path.exists('carteira.csv'):
        df = pd.read_csv('carteira.csv')
        df.columns = df.columns.str.strip().str.lower()
        for _, row in df.iterrows():
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
                patrimonio_total += valor_posicao
                
                analise = perguntar_ia(t, round(perf, 2), round(p_atual, 2))
                emoji = "🟢" if perf >= 0 else "🔴"
                info_carteira += f"{emoji} *{t}* | {perf:+.1f}% | ${valor_posicao:.2f}\n   💬 _{analise}_\n\n"
                time.sleep(0.4)
            except: continue

    if patrimonio_total > 0:
        gravar_historico(data_atual, patrimonio_total)

    # --- PARTE 2: RADAR GLOBAL (TOP 5 DE 10 DIAS) ---
    # Lista expandida com as ações mais influentes do mercado (Tech, Finanças, Saúde, Energia)
    radar_global = [
        "NVDA", "TSLA", "MSTR", "AMD", "PLTR", "AAPL", "MSFT", "AMZN", "META", "GOOGL",
        "AVGO", "ORCL", "NFLX", "COST", "SMCI", "COIN", "MARA", "RIOT", "PANW", "ARM",
        "BRK-B", "JPM", "V", "MA", "LLY", "UNH", "JNJ", "XOM", "CVX", "TSM", "ASML"
    ]
    
    lista_performance = []
    print("🔍 Analisando tendências de 10 dias...")

    for t in radar_global:
        try:
            acao = yf.Ticker(t)
            # Vamos buscar 15 dias para garantir que temos 10 dias úteis de dados
            h = acao.history(period="15d")
            if len(h) < 10: continue
            
            preco_hoje = h['Close'].iloc[-1]
            preco_10_dias = h['Close'].iloc[-10]
            var_10_dias = ((preco_hoje - preco_10_dias) / preco_10_dias) * 100
            
            if var_10_dias > 0:
                lista_performance.append({
                    'ticker': t, 
                    'var': var_10_dias, 
                    'preco': preco_hoje
                })
        except: continue

    # Ordenar pelas 5 maiores subidas nos últimos 10 dias
    top_5_global = sorted(lista_performance, key=lambda x: x['var'], reverse=True)[:5]
    
    radar_texto = ""
    for item in top_5_global:
        analise_r = perguntar_ia(item['ticker'], round(item['var'], 2), round(item['preco'], 2), "10 dias")
        radar_texto += f"🔥 *{item['ticker']}* (+{item['var']:.1f}% em 10d)\n   👉 _{analise_r}_\n\n"
        time.sleep(0.4)

    msg = (
        f"📦 *RELATÓRIO DIÁRIO - {data_atual}*\n"
        f"💰 Património Total: ${patrimonio_total:.2f}\n"
        f"{'─'*25}\n\n"
        f"{info_carteira if info_carteira else 'Carteira vazia.'}\n"
        f"🏆 *TOP 5 EXPLOSÕES (10 DIAS)*\n"
        f"{'─'*25}\n"
        f"{radar_texto if radar_texto else 'Sem movimentos expressivos.'}"
    )
    
    enviar_telegram(msg)
    print("✅ Relatório enviado!")

if __name__ == "__main__":
    executar_itisinvest()

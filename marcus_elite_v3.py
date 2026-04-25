import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from supabase import create_client, Client
import hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIG ---
st.set_page_config(page_title="Marcus.Ai Elite V4", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1 { text-align: center; color: #ff4b4b; text-shadow: 0px 0px 15px #ff4b4b; font-family: 'Monaco', monospace; }
    div[data-testid="stMetricValue"] { color: #00FF00 !important; }
    .stButton>button { width: 100%; background-color: #161b22; color: white; border: 1px solid #30363d; }
    .stButton>button:hover { border-color: #ff4b4b; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=12000, key="datarefresh")

def init_supabase():
    try: return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except: st.error("Secrets Error!"); st.stop()

supabase = init_supabase()
def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()

if 'auth' not in st.session_state: st.session_state.auth = False
if 'user' not in st.session_state: st.session_state.user = ""

# --- LOGIN (UI UNTOUCHED) ---
if not st.session_state.auth:
    st.markdown("<br><br><h1>MARCUS ELITE V4</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        m = st.tabs(["LOGIN", "CREATE ID"])
        with m[0]:
            u_in, p_in = st.text_input("USERNAME"), st.text_input("PASSWORD", type="password")
            if st.button("ACCESS"):
                res = supabase.table("users").select("*").eq("username", u_in).execute()
                if res.data and res.data[0]['password'] == make_hashes(p_in):
                    st.session_state.auth, st.session_state.user = True, u_in
                    st.rerun()
        with m[1]:
            u_n, p_n = st.text_input("NEW ID"), st.text_input("NEW KEY", type="password")
            if st.button("INITIALIZE"):
                try:
                    supabase.table("users").insert({"username": u_n, "password": make_hashes(p_n), "balance": 100000.0}).execute()
                    st.success("SUCCESS.")
                except: st.error("TAKEN.")

# --- TERMINAL ---
else:
    user = st.session_state.user
    bal_res = supabase.table("users").select("balance").eq("username", user).execute()
    balance = float(bal_res.data[0]['balance'])

    st.markdown(f"<h1>OPERATOR: {user.upper()}</h1>", unsafe_allow_html=True)
    
    tickers = [
        "BTC-USD", "ETH-USD", "SOL-USD", "NVDA", "AAPL", "TSLA", "AMD", "MSFT", "GOOGL", "AMZN", 
        "META", "NFLX", "COIN", "MARA", "RIOT", "MSTR", "PLTR", "BABA", "NIO", "XPEV", 
        "AMC", "GME", "BB", "SQ", "PYPL", "SHOP", "DIS", "T", "VZ", "F", "GM", "LCID", 
        "RIVN", "HOOD", "UBER", "LYFT", "ABNB", "COKE", "PEP", "KO", "SBUX", "WMT", 
        "COST", "TGT", "JPM", "BAC", "GS", "MS", "V", "MA", "DKNG", "PENN", "U", 
        "RBLX", "SNAP", "ZM", "PTON", "DASH", "OPEN", "SOFI", "AI", "C3AI", "PATH", 
        "SNOW", "NET", "CRWD", "OKTA", "ZS", "DDOG", "DOCU", "UPST", "AFRM", "CHPT", 
        "BLNK", "SPY", "QQQ", "IWM", "DIA", "GLD", "SLV", "USO", "UNG"
    ]
    ticker = st.sidebar.selectbox("ASSET", tickers)
    qty = st.sidebar.number_input("QTY", min_value=1, value=1)
    
    data = yf.download(ticker, period="1d", interval="1m")
    
    if not data.empty:
        df = data.copy()
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        live_p = float(df['Close'].values.flatten()[-1])
        y = df['Close'].values.flatten()
        slope = float((len(y) * (range(len(y)) * y).sum() - sum(range(len(y))) * sum(y)) / (len(y) * (sum([i**2 for i in range(len(y))])) - (sum(range(len(y)))**2)))

        # --- SIGNALS ---
        short_ema = df['Close'].ewm(span=9).mean().iloc[-1]
        long_ema = df['Close'].ewm(span=21).mean().iloc[-1]
        if slope > 0 and short_ema > long_ema: ai_sig = "🟢 BUY"
        elif slope < 0 and short_ema < long_ema: ai_sig = "🔴 SELL"
        else: ai_sig = "🟡 HOLD"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("LIVE PRICE", f"${live_p:,.2f}", delta=f"{slope:.4f}")
        c2.metric("SIGNAL", ai_sig)
        c3.metric("CASH", f"${balance:,.2f}")
        c4.metric("TOTAL P/L", f"${(balance-100000):,.2f}", delta=f"{(balance-100000):,.2f}", delta_color="normal")

        # --- CANDLESTICKS ---
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'].values.flatten(), high=df['High'].values.flatten(),
            low=df['Low'].values.flatten(), close=df['Close'].values.flatten(),
            increasing_line_color='#00ff00', decreasing_line_color='#ff0000'
        )])
        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, height=450, margin=dict(l=0,r=0,t=0,b=0), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        st.plotly_chart(fig, width='stretch', theme=None)

        if st.sidebar.button("EXECUTE BUY"):
            if balance >= (live_p * qty):
                new_bal = balance - (live_p * qty)
                supabase.table("users").update({"balance": new_bal}).eq("username", user).execute()
                supabase.table("trades").insert({"username": user, "symbol": ticker, "type": "BUY", "qty": qty, "price": live_p, "total": (live_p * qty), "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")}).execute()
                st.rerun()

        if st.sidebar.button("EXECUTE SELL"):
            new_bal = balance + (live_p * qty)
            supabase.table("users").update({"balance": new_bal}).eq("username", user).execute()
            supabase.table("trades").insert({"username": user, "symbol": ticker, "type": "SELL", "qty": qty, "price": live_p, "total": (live_p * qty), "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")}).execute()
            st.rerun()

    st.markdown("---")
    hist = supabase.table("trades").select("*").order("created_at", desc=True).limit(10).execute()
    if hist.data: st.dataframe(pd.DataFrame(hist.data)[['username', 'symbol', 'type', 'qty', 'price', 'total']], width='stretch')

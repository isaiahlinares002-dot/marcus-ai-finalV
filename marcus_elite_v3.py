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

# CSS: Center Login, Red Glow Title, Dark Theme
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    h1 { 
        text-align: center; color: #ff4b4b; 
        text-shadow: 0px 0px 15px #ff4b4b; 
        font-family: 'Monaco', monospace; letter-spacing: 2px;
    }
    div[data-testid="stMetricValue"] { color: #00FF00 !important; }
    .stButton>button { width: 100%; background-color: #161b22; color: white; border: 1px solid #30363d; }
    .stButton>button:hover { border-color: #ff4b4b; color: #ff4b4b; }
    </style>
    """, unsafe_allow_html=True)

st_autorefresh(interval=12000, key="datarefresh")

def init_supabase():
    try:
        return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
    except:
        st.error("Missing Secrets!")
        st.stop()

supabase = init_supabase()

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()

if 'auth' not in st.session_state: st.session_state.auth = False
if 'user' not in st.session_state: st.session_state.user = ""

# --- CENTERED LOGIN ---
if not st.session_state.auth:
    st.markdown("<br><br><h1>MARCUS ELITE V4</h1>", unsafe_allow_html=True)
    _, col2, _ = st.columns([1, 1.5, 1])
    with col2:
        mode = st.tabs(["LOGIN", "CREATE ID"])
        with mode[0]:
            u_in = st.text_input("USERNAME")
            p_in = st.text_input("PASSWORD", type="password")
            if st.button("ACCESS TERMINAL"):
                res = supabase.table("users").select("*").eq("username", u_in).execute()
                if res.data and res.data[0]['password'] == make_hashes(p_in):
                    st.session_state.auth, st.session_state.user = True, u_in
                    st.rerun()
                else: st.error("INVALID CREDENTIALS")
        with mode[1]:
            u_new, p_new = st.text_input("NEW USERNAME"), st.text_input("NEW PASSWORD", type="password")
            if st.button("INITIALIZE"):
                try:
                    supabase.table("users").insert({"username": u_new, "password": make_hashes(p_new), "balance": 100000.0}).execute()
                    st.success("ID CREATED.")
                except: st.error("ID TAKEN.")

# --- TRADING TERMINAL ---
else:
    user_name = st.session_state.user
    bal_res = supabase.table("users").select("balance").eq("username", user_name).execute()
    current_balance = float(bal_res.data[0]['balance'])

    st.markdown(f"<h1>OPERATOR: {user_name.upper()}</h1>", unsafe_allow_html=True)
    
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
    qty = st.sidebar.number_input("QUANTITY", min_value=1, value=1)
    
    data = yf.download(ticker, period="1d", interval="1m")
    if not data.empty:
        live_price = float(data['Close'].values.flatten()[-1])
        
        y = data['Close'].values.flatten()
        x = range(len(y))
        raw_slope = (len(x) * (x * y).sum() - sum(x) * sum(y)) / (len(x) * (sum([i**2 for i in x])) - (sum(x)**2))
        slope = float(raw_slope)

        m1, m2, m3 = st.columns(3)
        m1.metric("LIVE PRICE", f"${live_price:,.2f}", delta=f"{slope:.4f}")
        m2.metric("CASH", f"${current_balance:,.2f}")
        
        total_pl = current_balance - 100000.0
        m3.metric("TOTAL P/L", f"${total_pl:,.2f}", delta=f"{total_pl:,.2f}", delta_color="normal")

        # --- CANDLESTICK CHART ---
        fig = go.Figure(data=[go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            increasing_line_color='#00ff00', 
            decreasing_line_color='#ff0000'
        )])
        fig.update_layout(
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=500,
            margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)

        if st.sidebar.button("EXECUTE BUY"):
            cost = live_price * qty
            if current_balance >= cost:
                new_bal = current_balance - cost
                supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
                supabase.table("trades").insert({"username": user_name, "symbol": ticker, "type": "BUY", "qty": qty, "price": live_price, "total": cost, "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")}).execute()
                st.rerun()

        if st.sidebar.button("EXECUTE SELL"):
            rev = live_price * qty
            new_bal = current_balance + rev
            supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
            supabase.table("trades").insert({"username": user_name, "symbol": ticker, "type": "SELL", "qty": qty, "price": live_price, "total": rev, "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")}).execute()
            st.rerun()

    st.markdown("---")
    history = supabase.table("trades").select("*").order("created_at", desc=True).limit(50).execute()
    if history.data:
        st.dataframe(pd.DataFrame(history.data)[['username', 'symbol', 'type', 'qty', 'price', 'total']], use_container_width=True)

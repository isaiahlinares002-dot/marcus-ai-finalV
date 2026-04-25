import streamlit as st
import pandas as pd
import yfinance as yf
from supabase import create_client, Client
import hashlib
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

# --- CONFIGURATION & DATABASE ---
st.set_page_config(page_title="Marcus.Ai Elite V4", layout="wide", initial_sidebar_state="expanded")

# 12-Second Heartbeat (Auto-Refresh)
st_autorefresh(interval=12000, key="datarefresh")

def init_supabase():
    try:
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
        return create_client(url, key)
    except Exception as e:
        st.error("Missing Supabase Secrets! Add them in Streamlit Settings.")
        st.stop()

supabase: Client = init_supabase()

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

# --- AUTHENTICATION UI ---
st.sidebar.title("🛡️ Marcus.Ai Secure Gateway")
auth_mode = st.sidebar.selectbox("Mode", ["Login", "Sign Up"])
u = st.sidebar.text_input("Username")
p = st.sidebar.text_input("Password", type="password")

user_authenticated = False
user_name = ""
current_balance = 0.0

if auth_mode == "Sign Up":
    if st.sidebar.button("Initialize Terminal"):
        try:
            h_p = make_hashes(p)
            supabase.table("users").insert({"username": u, "password": h_p, "balance": 100000.0}).execute()
            st.sidebar.success("Account Created! Switch to Login.")
        except:
            st.sidebar.error("Username already exists or Database Error.")

if auth_mode == "Login":
    if u and p:
        res = supabase.table("users").select("*").eq("username", u).execute()
        if res.data:
            if res.data[0]['password'] == make_hashes(p):
                user_authenticated = True
                user_name = u
                current_balance = res.data[0]['balance']
            else:
                st.sidebar.error("Access Denied: Invalid Credentials")
        else:
            st.sidebar.error("User not found.")

# --- MAIN TERMINAL INTERFACE ---
if user_authenticated:
    st.title(f"📈 MARCUS ELITE V4 // OPERATOR: {user_name.upper()}")
    
    # 1. Sidebar Controls
    ticker = st.sidebar.selectbox("Select Asset", ["BTC-USD", "NVDA", "AAPL", "TSLA", "ETH-USD", "MSFT"])
    qty = st.sidebar.number_input("Quantity", min_value=1, value=1)
    
    # 2. Fetch Live Market Data
    data = yf.download(ticker, period="1d", interval="1m")
    if data.empty:
        st.error("Market Data Offline.")
        st.stop()
        
    live_price = data['Close'].iloc[-1]
    
    # 3. AI Signal Logic (Linear Regression)
    y = data['Close'].values
    x = range(len(y))
    slope = (len(x) * (x * y).sum() - sum(x) * sum(y)) / (len(x) * (sum([i**2 for i in x])) - (sum(x)**2))
    
    if slope > 0.01:
        signal, color = "📈 STRONG BUY", "#00FF00"
    elif slope < -0.01:
        signal, color = "📉 STRONG SELL", "#FF0000"
    else:
        signal, color = "⚖️ HOLD", "#808080"

    # 4. Top Metrics Bar
    m1, m2, m3 = st.columns(3)
    m1.metric("Live Price", f"${live_price:,.2f}", delta=f"{slope:.4f}")
    m2.metric("Portfolio Cash", f"${current_balance:,.2f}")
    
    # FIX: P/L calculation based on the initial 100k seed money
    total_pl = current_balance - 100000.0
    # delta_color="normal" ensures negatives are Red and positives are Green
    m3.metric("Total P/L", f"${total_pl:,.2f}", delta=f"{total_pl:,.2f}", delta_color="normal")

    # 5. Charting
    st.subheader(f"{ticker} Real-Time Analysis")
    st.line_chart(data['Close'])

    # 6. Trade Execution
    st.sidebar.markdown(f"### AI Signal: <span style='color:{color}'>{signal}</span>", unsafe_allow_html=True)
    
    col_buy, col_sell = st.sidebar.columns(2)
    
    if col_buy.button("EXECUTE BUY"):
        cost = live_price * qty
        if current_balance >= cost:
            new_bal = current_balance - cost
            supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
            supabase.table("trades").insert({
                "username": user_name, "symbol": ticker, "type": "BUY", 
                "qty": qty, "price": float(live_price), "total": float(cost),
                "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")
            }).execute()
            st.rerun()
        else:
            st.sidebar.error("Insufficient Funds")

    if col_sell.button("EXECUTE SELL"):
        revenue = live_price * qty
        new_bal = current_balance + revenue
        supabase.table("users").update({"balance": new_bal}).eq("username", user_name).execute()
        supabase.table("trades").insert({
            "username": user_name, "symbol": ticker, "type": "SELL", 
            "qty": qty, "price": float(live_price), "total": float(revenue),
            "date": datetime.now().strftime("%Y-%m-%d"), "time": datetime.now().strftime("%H:%M:%S")
        }).execute()
        st.rerun()

    # 7. Live Trading Ledger (Multi-user)
    st.markdown("---")
    st.subheader("📊 Global Live Trading Ledger")
    history = supabase.table("trades").select("*").order("created_at", desc=True).limit(50).execute()
    if history.data:
        df_ledger = pd.DataFrame(history.data)[['username', 'date', 'time', 'symbol', 'type', 'qty', 'price', 'total']]
        st.dataframe(df_ledger, use_container_width=True)
    else:
        st.info("No trades executed yet.")

else:
    st.warning("Please Login or Sign Up via the sidebar to access the Elite Terminal.")
    st.image("https://images.unsplash.com/photo-1611974717482-53907361a93e?auto=format&fit=crop&q=80&w=1000", caption="Marcus AI Pro Terminal v4.0")

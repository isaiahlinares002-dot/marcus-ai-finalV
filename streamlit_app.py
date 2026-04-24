import streamlit as st
import pandas as pd
import yfinance as yf
from datetime import datetime
import pytz
import os

# 1. PAGE SETUP & STYLING
st.set_page_config(page_title="Marcus.Ai Terminal", layout="wide")

# CSS for the distinct Manual Buy/Sell Button colors
st.markdown("""
    <style>
    /* Buy Button Styling (Green) */
    div.stButton > button:first-child {
        background-color: #28a745;
        color: white;
        font-weight: bold;
        height: 3.5em;
        width: 100%;
    }
    /* Sell Button Styling (Red) */
    div[data-testid="stVerticalBlock"] > div:nth-child(2) div.stButton > button {
        background-color: #dc3545;
        color: white;
        font-weight: bold;
        height: 3.5em;
        width: 100%;
    }
    </style>
""", unsafe_allow_html=True)

# 2. TIME & TICKER CONFIG
toronto_tz = pytz.timezone('America/Toronto')
current_time = datetime.now(toronto_tz).strftime("%H:%M:%S")

st.sidebar.title("🤖 Marcus.Ai Terminal")
# Updated with fast-moving penny stocks and high-volatility names
ticker_symbol = st.sidebar.selectbox("Select Ticker", 
    ["MAPS", "VFF", "LFVN", "BABB", "TSLA", "NVDA", "AMD"])

# 3. POSITION SIZING (This is how you make more than cents!)
st.sidebar.markdown("---")
st.sidebar.subheader("Position Sizing")
quantity = st.sidebar.slider("Number of Shares", min_value=1, max_value=10000, value=1000, step=100)

# 4. ADMIN TOOLS
if st.sidebar.button("🗑️ Reset All Trade Data"):
    df_empty = pd.DataFrame(columns=['Ticker', 'Action', 'Qty', 'Price', 'Total', 'Time'])
    df_empty.to_csv('journal.csv', index=False)
    st.sidebar.success("Journal Wiped!")
    st.rerun()

# 5. DATA FETCHING (1-Minute Intervals for 5-10 min Scalping)
try:
    ticker_data = yf.Ticker(ticker_symbol)
    df_price = ticker_data.history(period="1d", interval="1m")
    current_price = round(df_price['Close'].iloc[-1], 2)
    total_value = round(quantity * current_price, 2)
except:
    st.error("Market is closed or data connection lost.")
    current_price = 0.0

# 6. DASHBOARD DISPLAY
st.title(f"⚡ {ticker_symbol} Scalping Terminal")
c1, c2, c3 = st.columns(3)
c1.metric("Current Price", f"${current_price}")
c2.metric("Trade Size", f"{quantity} Shares")
c3.metric("Total Value", f"${total_value}")

st.subheader("Last 60 Minutes (High-Speed View)")
st.line_chart(df_price['Close'].tail(60))

# 7. EXECUTION PANEL
st.markdown("### 🕹️ Manual Execution")
col_buy, col_sell = st.columns(2)

with col_buy:
    if st.button(f"🚀 BUY {quantity} {ticker_symbol}"):
        new_row = {'Ticker': ticker_symbol, 'Action': 'BUY', 'Qty': quantity, 'Price': current_price, 'Total': total_value, 'Time': current_time}
        df = pd.read_csv('journal.csv') if os.path.exists('journal.csv') else pd.DataFrame(columns=['Ticker', 'Action', 'Qty', 'Price', 'Total', 'Time'])
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv('journal.csv', index=False)
        st.toast(f"Entered position at ${current_price}")

with col_sell:
    if st.button(f"💰 SELL {quantity} {ticker_symbol}"):
        new_row = {'Ticker': ticker_symbol, 'Action': 'SELL', 'Qty': quantity, 'Price': current_price, 'Total': total_value, 'Time': current_time}
        df = pd.read_csv('journal.csv') if os.path.exists('journal.csv') else pd.DataFrame(columns=['Ticker', 'Action', 'Qty', 'Price', 'Total', 'Time'])
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
        df.to_csv('journal.csv', index=False)
        st.toast(f"Exited position at ${current_price}")

# 8. PERFORMANCE JOURNAL
st.markdown("---")
st.subheader("📋 Performance Journal")
if os.path.exists('journal.csv'):
    display_df = pd.read_csv('journal.csv')
    # Use tail(15) so you can see your recent history clearly
    st.dataframe(display_df.tail(15), use_container_width=True)
else:
    st.write("No trades recorded today.")
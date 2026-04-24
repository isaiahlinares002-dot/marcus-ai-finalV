import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from sklearn.linear_model import LinearRegression
from plotly.subplots import make_subplots

# 1. PAGE CONFIG & ELITE THEME
st.set_page_config(page_title="Marcus.Ai Elite V3", layout="wide")
st.markdown("""
    <style>
    .main { background-color: #0e1117; color: #ffffff; }
    .stMetric { background-color: #1a1c23; padding: 15px; border-radius: 12px; border: 1px solid #30363d; }
    </style>
    """, unsafe_allow_html=True)

# 2. WATCHLIST (Including Crypto for 24/7 Testing)
tickers = ["BTC-USD", "ETH-USD", "TSLA", "NVDA", "VFF", "LFVN", "BABB", "MARS"]
st.sidebar.header("🕹️ Marcus.Ai Control")
ticker = st.sidebar.selectbox("🎯 Target Asset", tickers)
qty = st.sidebar.number_input("Shares/Units", value=100)

st.title(f"🚀 Marcus.Ai Elite Terminal: {ticker}")

# 3. LIVE DATA ENGINE
def get_live_data(symbol):
    try:
        data = yf.download(symbol, period="1d", interval="1m")
        if data.empty: return None
        # Technical Indicators
        data['MA10'] = data['Close'].rolling(10).mean()
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        data['RSI'] = 100 - (100 / (1 + gain/loss))
        return data
    except:
        return None

df = get_live_data(ticker)

if df is not None and len(df) > 20:
    # 4. AI PREDICTION MODEL
    df_ai = df.tail(20).reset_index()
    X = np.array(df_ai.index).reshape(-1, 1)
    y = df_ai['Close'].values
    ai_model = LinearRegression().fit(X, y)
    
    # FIX: Using .item() to convert numpy array to a single float number
    raw_prediction = ai_model.predict(np.array([[len(df_ai) + 5]]))[0]
    prediction = float(raw_prediction.item()) if hasattr(raw_prediction, 'item') else float(raw_prediction)
    slope = ai_model.coef_[0]

    # 5. PROFESSIONAL CANDLESTICK VISUALS
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.03, row_heights=[0.7, 0.3])
    
    # Candlestick Bars
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'], name="Price"
    ), row=1, col=1)
    
    # Volume Bar
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", marker_color='cyan', opacity=0.4), row=2, col=1)
    
    fig.update_layout(height=600, template="plotly_dark", xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    # 6. METRICS & AI SIGNAL ENGINE
    curr_price = float(df['Close'].iloc[-1])
    rsi = float(df['RSI'].iloc[-1])
    total_value = round(curr_price * qty, 2)

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Market Price", f"${round(curr_price, 4)}")
        st.write(f"AI Prediction (5m): **${round(prediction, 4)}**")

    with col2:
        st.metric("RSI Momentum", f"{round(rsi, 1)}")
        if rsi > 70: st.error("🔥 OVERBOUGHT")
        elif rsi < 30: st.success("🧊 OVERSOLD")
        else: st.info("⚖️ Neutral")

    with col3:
        st.metric("Total Value", f"${total_value:,}")
        if slope > 0.001 and rsi < 65:
            st.success("🤖 AI: STRONG BUY")
        elif slope < -0.001 and rsi > 35:
            st.error("🤖 AI: STRONG SELL")
        else:
            st.warning("🤖 AI: HOLD / WATCH")

else:
    st.header("🌙 Market is Resting")
    st.info("💡 **Switch to BTC-USD** in the sidebar to see the AI trade Crypto live!")
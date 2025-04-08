import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
from io import BytesIO

# Página
st.set_page_config(page_title="Stock Info Terminal", layout="centered")

@st.cache_data
def get_stock_info(symbol):
    try:
        stock = yf.Ticker(symbol)
        return stock.info
    except Exception:
        return None

@st.cache_data
def get_stock_history(symbol):
    stock = yf.Ticker(symbol)
    return stock.history(period="5y", auto_adjust=False)

def plot_candlestick_chart(history, symbol):
    history.index = pd.to_datetime(history.index)
    style = mpf.make_mpf_style(base_mpf_style='yahoo', rc={'font.size': 10})
    fig, ax = mpf.plot(history, type='candle', style=style, title=f"{symbol} - 5 Year History", volume=True, returnfig=True)
    st.pyplot(fig)

def plot_adjusted_close_line_chart(history, symbol):
    adj_col = None
    for col in history.columns:
        if col.lower().replace(" ", "") == "adjclose":
            adj_col = col
            break

    if not adj_col:
        st.warning("⚠️ Adjusted close data not available for this symbol.")
        return

    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(history.index, history[adj_col], label='Adjusted Close', linewidth=1.8)
    ax.set_title(f"Precio histórico de cierre ajustado - {symbol} (2019–2024)", fontsize=14)
    ax.set_xlabel("Fecha", fontsize=12)
    ax.set_ylabel("Precio (USD)", fontsize=12)
    ax.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    st.pyplot(fig)

def calculate_cagr(history, years):
    adj_col = None
    for col in history.columns:
        if col.lower().replace(" ", "") == "adjclose":
            adj_col = col
            break

    if not adj_col or len(history) == 0:
        return None

    end_price = history[adj_col].iloc[-1]
    start_price = history[adj_col].resample('1D').ffill().dropna()

    cagr_results = {}
    for yr in years:
        days = 252 * yr
        if len(start_price) >= days:
            start = start_price.iloc[-days]
            cagr = ((end_price / start) ** (1 / yr)) - 1
            cagr_results[f"{yr}Y"] = round(cagr * 100, 2)
        else:
            cagr_results[f"{yr}Y"] = "N/A"
    return cagr_results

def calculate_annual_volatility(history):
    adj_col = None
    for col in history.columns:
        if col.lower().replace(" ", "") == "adjclose":
            adj_col = col
            break

    if not adj_col or len(history) < 2:
        return None

    daily_returns = history[adj_col].pct_change().dropna()
    daily_vol = np.std(daily_returns)
    annual_vol = daily_vol * np.sqrt(252)
    return round(annual_vol * 100, 2)

def export_csv(data):
    csv = data.to_csv(index=False).encode('utf-8')
    st.download_button(label="📥 Download CSV", data=csv, file_name="company_data.csv", mime="text/csv")

def export_pdf(info):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    pdf.cell(200, 10, txt="Stock Information", ln=True, align='C')
    pdf.ln(10)

    for key, value in info.items():
        try:
            pdf.cell(200, 10, txt=f"{key}: {value}", ln=True, align='L')
        except:
            continue

    pdf_bytes = pdf.output(dest='S').encode('latin1')
    st.download_button(
        label="📥 Download PDF",
        data=pdf_bytes,
        file_name="company_data.pdf",
        mime="application/pdf"
    )

# Interfaz
st.title("📈 Stock Info Terminal with Charts, Returns & Risk")

query = st.text_input("🔍 Enter stock symbol (e.g. AAPL, MSFT, TSLA)", "").upper()

if query:
    stock_info = get_stock_info(query)

    if stock_info and "longName" in stock_info:
        st.subheader(stock_info["longName"])

        description = stock_info.get("longBusinessSummary", "No description available.")
        st.markdown("*📘 Company Description:*")
        st.write(description)

        col1, col2 = st.columns(2)
        with col1:
            st.metric("Sector", stock_info.get("sector", "N/A"))
            st.metric("Industry", stock_info.get("industry", "N/A"))
            st.metric("Market Cap", f"${stock_info.get('marketCap', 'N/A'):,}")
        with col2:
            st.metric("Current Price", f"${stock_info.get('currentPrice', 'N/A')}")
            st.metric("52W Low", f"${stock_info.get('fiftyTwoWeekLow', 'N/A')}")
            st.metric("52W High", f"${stock_info.get('fiftyTwoWeekHigh', 'N/A')}")

        history = get_stock_history(query)
        if not history.empty:
            st.subheader("📊 Candlestick Chart")
            st.markdown("This chart shows 5 years of historical price movements using candlesticks.")
            plot_candlestick_chart(history, query)

            st.subheader("📈 Adjusted Close Price History (Line Chart)")
            st.markdown("Line chart of the adjusted closing price over the last 5 years.")
            plot_adjusted_close_line_chart(history, query)

            st.subheader("📉 Annualized Returns (CAGR)")
            st.markdown("This calculation considers the price at the beginning and end of the period to determine the annualized return.")
            cagr_data = calculate_cagr(history, [1, 3, 5])
            if cagr_data:
                cagr_df = pd.DataFrame(list(cagr_data.items()), columns=["Period", "Annualized Return (%)"])
                st.table(cagr_df)
                st.markdown("🧠 *The annualized return was calculated using the CAGR formula.*")

            st.subheader("⚠️ Annual Risk (Volatility)")
            st.markdown("Volatility is calculated from the standard deviation of daily returns and annualized by multiplying by √252.")
            annual_vol = calculate_annual_volatility(history)
            if annual_vol is not None:
                st.metric("Annual Volatility", f"{annual_vol}%")
                st.markdown("🧠 *This value represents the asset's historical annual volatility, measured by the standard deviation of daily returns.*")

        st.subheader("📂 Export Data")
        data_to_export = pd.DataFrame.from_dict(stock_info, orient="index", columns=["Value"]).reset_index()
        export_csv(data_to_export)
        export_pdf(stock_info)
    else:
        st.error("❌ Incorrect symbol, please try again.")
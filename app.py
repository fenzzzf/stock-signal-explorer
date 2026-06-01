from datetime import date

import pandas as pd
import streamlit as st
import yfinance as yf


st.set_page_config(
    page_title="Stock Signal Explorer",
    layout="wide",
)


def format_currency(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"${value:,.2f}"


def format_percent(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


def format_market_cap(value):
    if value is None or pd.isna(value):
        return "N/A"

    units = [
        (1_000_000_000_000, "T"),
        (1_000_000_000, "B"),
        (1_000_000, "M"),
    ]

    for amount, suffix in units:
        if abs(value) >= amount:
            return f"${value / amount:,.2f}{suffix}"

    return f"${value:,.0f}"


def format_number(value):
    if value is None or pd.isna(value):
        return "N/A"
    return f"{value:,}"


@st.cache_data(ttl=900)
def load_stock_data(ticker, period):
    stock = yf.Ticker(ticker)
    history = stock.history(period=period)
    info = stock.info
    return history, info


def calculate_indicators(history, info):
    data = history.copy()
    data["MA50"] = data["Close"].rolling(window=50).mean()
    data["MA200"] = data["Close"].rolling(window=200).mean()

    latest_close = data["Close"].iloc[-1]
    first_close = data["Close"].iloc[0]
    recent_change = ((latest_close - first_close) / first_close) * 100

    daily_returns = data["Close"].pct_change().dropna()
    volatility = daily_returns.std() * (252**0.5) * 100

    pe_ratio = info.get("trailingPE") or info.get("forwardPE")
    ma50 = data["MA50"].iloc[-1]
    ma200 = data["MA200"].iloc[-1]

    return {
        "data": data,
        "latest_close": latest_close,
        "recent_change": recent_change,
        "volatility": volatility,
        "pe_ratio": pe_ratio,
        "ma50": ma50,
        "ma200": ma200,
    }


def generate_signal(indicators):
    score = 0
    reasons = []

    latest_close = indicators["latest_close"]
    ma50 = indicators["ma50"]
    ma200 = indicators["ma200"]
    recent_change = indicators["recent_change"]
    volatility = indicators["volatility"]
    pe_ratio = indicators["pe_ratio"]

    if not pd.isna(ma50):
        if latest_close > ma50:
            score += 1
            reasons.append("The latest price is above the 50-day moving average, which can show short-term strength.")
        else:
            score -= 1
            reasons.append("The latest price is below the 50-day moving average, which can show short-term weakness.")

    if not pd.isna(ma200):
        if latest_close > ma200:
            score += 1
            reasons.append("The latest price is above the 200-day moving average, which can show a stronger long-term trend.")
        else:
            score -= 1
            reasons.append("The latest price is below the 200-day moving average, which can show long-term caution.")

    if recent_change > 5:
        score += 1
        reasons.append("The stock is up more than 5% over the selected period.")
    elif recent_change < -5:
        score -= 1
        reasons.append("The stock is down more than 5% over the selected period.")
    else:
        reasons.append("The recent percentage change is moderate.")

    if volatility < 25:
        score += 1
        reasons.append("Volatility is relatively low, suggesting steadier price movement.")
    elif volatility > 45:
        score -= 1
        reasons.append("Volatility is high, which means the price has been moving more unpredictably.")
    else:
        reasons.append("Volatility is in a middle range.")

    if pe_ratio is not None and not pd.isna(pe_ratio):
        if pe_ratio < 15:
            score += 1
            reasons.append("The P/E ratio is below 15, which may suggest the stock is not expensive compared with earnings.")
        elif pe_ratio > 35:
            score -= 1
            reasons.append("The P/E ratio is above 35, which may suggest the stock is expensive compared with earnings.")
        else:
            reasons.append("The P/E ratio is in a moderate range.")
    else:
        reasons.append("P/E ratio was not available from Yahoo Finance for this ticker.")

    if score >= 3:
        signal = "Buy"
        summary = "The rule-based score is positive across several indicators."
    elif score <= -2:
        signal = "Avoid"
        summary = "The rule-based score shows more warning signs than strengths."
    else:
        signal = "Hold"
        summary = "The indicators are mixed, so the rule-based result is neutral."

    return signal, score, summary, reasons


st.title("Stock Signal Explorer")
st.caption("A simple rule-based stock analysis app for a high school capstone project.")

with st.sidebar:
    st.header("Search")
    ticker = st.text_input("Stock ticker", value="AAPL").strip().upper()
    period = st.selectbox(
        "Data period",
        ["6mo", "1y", "2y", "5y"],
        index=1,
        help="Longer periods make the 200-day moving average more reliable.",
    )
    st.divider()
    st.write("This app uses Yahoo Finance data through `yfinance`.")

if not ticker:
    st.info("Enter a stock ticker to begin.")
    st.stop()

try:
    history, info = load_stock_data(ticker, period)
except Exception as error:
    st.error(f"Could not load data for {ticker}. Try another ticker.")
    st.caption(f"Details: {error}")
    st.stop()

if history.empty:
    st.error(f"No recent price data was found for {ticker}. Check the ticker symbol and try again.")
    st.stop()

indicators = calculate_indicators(history, info)
signal, score, summary, reasons = generate_signal(indicators)
chart_data = indicators["data"][["Close", "MA50", "MA200"]]

company_name = info.get("longName") or info.get("shortName") or ticker
start_date = history.index.min().date()
end_date = history.index.max().date()

st.subheader(f"{company_name} ({ticker})")
st.write(f"Showing data from {start_date} to {end_date}.")

st.subheader("Company Basic Information")
basic_info = {
    "Company name": company_name,
    "Sector": info.get("sector") or "N/A",
    "Industry": info.get("industry") or "N/A",
    "Country": info.get("country") or "N/A",
    "Website": info.get("website") or "N/A",
    "Market cap": format_market_cap(info.get("marketCap")),
    "Full-time employees": format_number(info.get("fullTimeEmployees")),
}

info_cols = st.columns(2)
info_items = list(basic_info.items())
for index, (label, value) in enumerate(info_items):
    with info_cols[index % 2]:
        st.markdown(f"**{label}**")
        if label == "Website" and value != "N/A":
            st.markdown(f"[{value}]({value})")
        else:
            st.write(value)

business_summary = info.get("longBusinessSummary") or "N/A"
with st.expander("Company Business Summary"):
    st.write(business_summary)

signal_color = {
    "Buy": "normal",
    "Hold": "off",
    "Avoid": "inverse",
}[signal]

metric_cols = st.columns(5)
metric_cols[0].metric("Signal", signal, f"Score: {score}", delta_color=signal_color)
metric_cols[1].metric("Latest close", format_currency(indicators["latest_close"]))
metric_cols[2].metric("Recent change", format_percent(indicators["recent_change"]))
metric_cols[3].metric("Volatility", format_percent(indicators["volatility"]))
metric_cols[4].metric("P/E ratio", "N/A" if indicators["pe_ratio"] is None else f"{indicators['pe_ratio']:.2f}")

st.divider()

left, right = st.columns([2, 1])

with left:
    st.subheader("Price Chart")
    st.line_chart(chart_data)

with right:
    st.subheader("Result Explanation")
    st.write(summary)
    for reason in reasons:
        st.write(f"- {reason}")

st.subheader("Indicator Table")
table = pd.DataFrame(
    {
        "Indicator": [
            "Latest close",
            "50-day moving average",
            "200-day moving average",
            "Recent percentage change",
            "Annualized volatility",
            "P/E ratio",
        ],
        "Value": [
            format_currency(indicators["latest_close"]),
            format_currency(indicators["ma50"]),
            format_currency(indicators["ma200"]),
            format_percent(indicators["recent_change"]),
            format_percent(indicators["volatility"]),
            "N/A" if indicators["pe_ratio"] is None else f"{indicators['pe_ratio']:.2f}",
        ],
        "What it means": [
            "Most recent closing price in the selected data.",
            "Average closing price over the last 50 trading days.",
            "Average closing price over the last 200 trading days.",
            "How much the stock changed over the selected period.",
            "A rough measure of how much the stock price moves up and down.",
            "Price compared with company earnings, when available.",
        ],
    }
)
st.dataframe(table, hide_index=True, use_container_width=True)

with st.expander("How the Buy, Hold, or Avoid score works"):
    st.write(
        """
        The app adds or subtracts points using simple rules:

        - Price above moving averages adds points; price below them subtracts points.
        - A recent gain above 5% adds a point; a recent drop below -5% subtracts a point.
        - Lower volatility adds a point; very high volatility subtracts a point.
        - A lower P/E ratio can add a point, while a very high P/E ratio can subtract one.

        This is intentionally simple so the logic is easy to understand and explain.
        """
    )

st.warning(
    "Disclaimer: This app is for education only and is not financial advice. "
    "Do your own research and talk to a qualified financial professional before making investment decisions."
)

st.caption(f"Last checked in the app: {date.today().isoformat()}")

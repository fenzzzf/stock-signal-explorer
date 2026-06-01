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
    return f"{int(value):,}"


def get_risk_level(volatility):
    if volatility < 20:
        return "Low Risk"
    if volatility <= 40:
        return "Medium Risk"
    return "High Risk"


def get_confidence_score(signal, score):
    if signal == "Buy":
        return 90 if score >= 4 else 78
    if signal == "Avoid":
        return max(20, min(40, 40 + (score * 5)))
    return max(40, min(60, 50 + (score * 5)))


def get_signal_label(signal):
    icons = {
        "Buy": "🟢",
        "Hold": "🟡",
        "Avoid": "🔴",
    }
    return f"{icons[signal]} {signal}"


def build_ai_summary(company_name, indicators, signal):
    latest_close = indicators["latest_close"]
    ma50 = indicators["ma50"]
    ma200 = indicators["ma200"]
    recent_change = indicators["recent_change"]
    volatility = indicators["volatility"]
    pe_ratio = indicators["pe_ratio"]

    ma_parts = []
    if not pd.isna(ma50):
        ma_parts.append("above its 50-day moving average" if latest_close > ma50 else "below its 50-day moving average")
    if not pd.isna(ma200):
        ma_parts.append("above its 200-day moving average" if latest_close > ma200 else "below its 200-day moving average")

    if ma_parts:
        trend_sentence = f"{company_name} is currently trading {' and '.join(ma_parts)}, which helps describe the current trend."
    else:
        trend_sentence = f"{company_name} does not have enough data for all moving-average comparisons yet."

    if volatility < 20:
        volatility_text = "low"
    elif volatility <= 40:
        volatility_text = "moderate"
    else:
        volatility_text = "high"

    if pe_ratio is None or pd.isna(pe_ratio):
        pe_sentence = "A P/E ratio was not available, so valuation is not included in that part of the analysis."
    else:
        pe_sentence = f"The P/E ratio is {pe_ratio:.2f}, which gives a simple valuation reference."

    outlook = {
        "Buy": "bullish",
        "Hold": "neutral",
        "Avoid": "cautious",
    }[signal]

    return (
        f"{trend_sentence} The stock changed {recent_change:.2f}% during the selected period, "
        f"and volatility is {volatility_text} at {volatility:.2f}%. {pe_sentence} "
        f"Based on the rule-based indicators, the overall outlook is {outlook}."
    )


@st.cache_data(ttl=900)
def load_stock_data(ticker, period):
    stock = yf.Ticker(ticker)
    history = pd.DataFrame()
    info = {}
    history_error = None
    info_error = None

    try:
        history = stock.history(period=period)
    except Exception as error:
        history_error = error

    try:
        info = stock.info or {}
    except Exception as error:
        info_error = error

    return history, info, history_error, info_error


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
    ticker = st.text_input("Stock ticker", value="MSFT").strip().upper()
    period = st.selectbox(
        "Data period",
        ["6mo", "1y", "2y", "5y"],
        index=1,
        help="Longer periods make the 200-day moving average more reliable.",
    )
    st.divider()
    st.write("This app uses Yahoo Finance data through `yfinance`.")
    st.write("Examples: US: MSFT, NVDA, TSLA | Hong Kong: 0700.HK | Canada: SHOP.TO | China: 600519.SS")

if not ticker:
    st.info("Enter a stock ticker to begin.")
    st.stop()

try:
    history, info, history_error, info_error = load_stock_data(ticker, period)
except Exception as error:
    st.error(
        f"Sorry, the app could not load data for {ticker}. "
        "Please check the ticker symbol or try again in a few minutes."
    )
    st.stop()

if history.empty:
    st.error(
        f"Sorry, no recent price data was found for {ticker}. "
        "Yahoo Finance may be temporarily unavailable, or the ticker symbol may not exist."
    )
    st.stop()

company_info_unavailable = bool(info_error) or not info
if company_info_unavailable:
    st.warning("Company information is temporarily unavailable due to Yahoo Finance rate limits.")

indicators = calculate_indicators(history, info)
signal, score, summary, reasons = generate_signal(indicators)
risk_level = get_risk_level(indicators["volatility"])
confidence_score = get_confidence_score(signal, score)
signal_label = get_signal_label(signal)
chart_data = indicators["data"][["Close", "MA50", "MA200"]]

company_name = info.get("longName") or info.get("shortName") or ticker
start_date = history.index.min().date()
end_date = history.index.max().date()
ai_summary = build_ai_summary(company_name, indicators, signal)

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

status_cols = st.columns(3)
status_cols[0].metric("Signal", signal_label, f"Score: {score}", delta_color=signal_color)
status_cols[1].metric("Risk Level", risk_level)
status_cols[2].metric("Confidence", f"{confidence_score}%")

market_cols = st.columns(4)
market_cols[0].metric("Latest close", format_currency(indicators["latest_close"]))
market_cols[1].metric("Recent change", format_percent(indicators["recent_change"]))
market_cols[2].metric("Volatility", format_percent(indicators["volatility"]))
market_cols[3].metric("P/E ratio", "N/A" if indicators["pe_ratio"] is None else f"{indicators['pe_ratio']:.2f}")

st.divider()

st.subheader("AI Investment Summary")
st.write(ai_summary)

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

# Stock Signal Explorer

A simple Streamlit app for a high school capstone project. Users enter a stock ticker, and the app fetches recent market data with `yfinance`, calculates basic indicators, and gives a rule-based `Buy`, `Hold`, or `Avoid` result.

## Features

- Stock ticker input
- Recent stock data from Yahoo Finance through `yfinance`
- Company basic information, including sector, industry, country, website, market cap, employees, and business summary
- 50-day and 200-day moving averages
- Recent percentage change
- Annualized volatility
- Risk Level based on volatility
- Confidence Score based on the rule-based signal score
- P/E ratio when available
- Price chart with moving averages
- AI Investment Summary generated from the indicators
- Plain-English explanation of the result
- Friendly handling when Yahoo Finance temporarily rate-limits company information
- Educational disclaimer

## New Analysis Features

The app now includes a few extra capstone-friendly features:

- **Risk Level:** labels the stock as Low Risk, Medium Risk, or High Risk based on volatility.
- **Confidence Score:** converts the rule-based score into a simple percentage from 0% to 100%.
- **AI Investment Summary:** creates a short, beginner-friendly paragraph using moving averages, recent percentage change, volatility, P/E ratio, and the final signal.
- **Rate-limit handling:** if Yahoo Finance temporarily blocks company information, the app still shows the stock chart and indicators when price data is available.

## How to Run

Install the dependencies:

```bash
pip install -r requirements.txt
```

Start the app:

```bash
streamlit run app.py
```

## Important Note

This project is for education only. It is not financial advice and should not be used as the only reason to buy or sell a stock.

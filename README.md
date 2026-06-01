# Stock Signal Explorer

A simple Streamlit app for a high school capstone project. Users enter a stock ticker, and the app fetches recent market data with `yfinance`, calculates basic indicators, and gives a rule-based `Buy`, `Hold`, or `Avoid` result.

## Features

- Stock ticker input
- Recent stock data from Yahoo Finance through `yfinance`
- Company basic information, including sector, industry, country, website, market cap, employees, and business summary
- 50-day and 200-day moving averages
- Recent percentage change
- Annualized volatility
- P/E ratio when available
- Price chart with moving averages
- Plain-English explanation of the result
- Educational disclaimer

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

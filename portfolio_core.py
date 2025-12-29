import logging
import os
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime

logger = logging.getLogger(__name__)
logger.addHandler(logging.NullHandler())

def calculate_asset_profit(current_price, units, buy_price):
    return (current_price - buy_price) * units

def load_portfolio_data(file_path="portfolio.csv"):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Portfolio file not found: {file_path}")

    df = pd.read_csv(file_path)

    # Ticker and Units required; BuyPrice optional
    required_columns = {"Ticker", "Units"}
    if not required_columns.issubset(df.columns):
        raise ValueError(f"Portfolio file must contain the following columns: {required_columns}")

    # Ensure proper dtypes and fill missing BuyPrice with NaN
    df = df.copy()
    df["Ticker"] = df["Ticker"].astype(str).str.strip()
    # Coerce Units to numeric, invalid -> NaN
    df["Units"] = pd.to_numeric(df["Units"], errors="coerce")
    if "BuyPrice" in df.columns:
        df["BuyPrice"] = pd.to_numeric(df["BuyPrice"], errors="coerce")
    else:
        df["BuyPrice"] = pd.NA

    return df

def calculate_portfolio_value(portfolio_df):
    """
    Returns:
    details_df: pandas.DataFrame with per-asset metrics
    total_value: float total current market value
    total_profit: float total profit (ignores assets without BuyPrice)
    """
    results = []
    total_value = 0.0
    total_profit = 0.0

    # iterate rows
    for _, row in portfolio_df.iterrows():
        ticker = str(row.get("Ticker", "")).strip()
        units = row.get("Units", None)
        buy_price = row.get("BuyPrice", None)

        if not ticker:
            logger.warning("Skipping row with missing ticker")
            continue

        if units is None or pd.isna(units) or not isinstance(units, (int, float)) or units <= 0:
            logger.warning(f"Skipping {ticker} due to invalid units: {units}")
            continue

        # fetch 1y history (used for current price, 52w range, and day change)
        hist = get_ticker_year_history(ticker)
        if hist.empty or "Close" not in hist.columns:
            logger.warning(f"No usable price history for {ticker}. Skipped.")
            continue

        # current price: last close
        try:
            current_price = float(hist["Close"].dropna().iloc[-1])
        except Exception:
            logger.warning(f"Unable to determine current price for {ticker}. Skipped.")
            continue

        # day change: use last two closes if available
        closes = hist["Close"].dropna()
        day_pct = None
        if len(closes) >= 2:
            prev = float(closes.iloc[-2])
            if prev != 0:
                day_pct = (current_price - prev) / prev * 100.0

        # 52-week high/low from history
        try:
            high_52 = float(closes.max())
            low_52 = float(closes.min())
        except Exception:
            high_52 = None
            low_52 = None

        # get basic info (name, market cap) - may be slow but useful
        info = get_ticker_info(ticker)
        name = info.get("name")
        market_cap = info.get("marketCap")

        # value and profit
        value = current_price * float(units)
        if pd.notna(buy_price) and isinstance(buy_price, (int, float)):
            profit = calculate_asset_profit(current_price, float(units), float(buy_price))
            # return %
            return_pct = None
            cost_basis = float(buy_price) * float(units)
            if buy_price != 0:
                return_pct = profit / cost_basis * 100.0
        else:
            profit = None
            return_pct = None
            cost_basis = None

        total_value += value
        if profit is not None:
            total_profit += profit

        results.append({
            "Ticker": ticker,
            "Name": name,
            "Units": units,
            "Buy Price": buy_price if pd.notna(buy_price) else None,
            "Cost Basis": cost_basis,
            "Current Price": current_price,
            "Value": value,
            "Profit": profit,
            "Return %": return_pct,
            "Day %": day_pct,
            "52W High": high_52,
            "52W Low": low_52,
            "MarketCap": market_cap
        })

    # create DataFrame and compute allocation weights
    df = pd.DataFrame(results)
    if df.empty:
        return df, total_value, total_profit

    # compute weight %
    df["Weight %"] = (df["Value"] / total_value * 100).round(4)
    # Sort by Value desc
    df = df.sort_values("Value", ascending=False).reset_index(drop=True)

    # rounding for presentation
    for col in ["Current Price", "Value", "Profit", "Cost Basis", "MarketCap", "52W High", "52W Low", "Return %", "Day %"]:
        if col in df.columns:
            # avoid converting None to float in presence of missing values
            df[col] = pd.to_numeric(df[col], errors="coerce")

    return df, total_value, total_profit

def portfolio_time_series(portfolio_df, start="2016-01-01"):
    """
    Build a time series of total portfolio value from `start` to today.
    Uses yf.download for multiple tickers at once for efficiency.
    Returns a pandas Series indexed by date with portfolio total value.
    """
    tickers = [t for t in portfolio_df["Ticker"].astype(str).tolist() if t]
    if not tickers:
        return pd.Series(dtype=float)

    # get Close prices for all tickers in one download
    try:
        data = yf.download(tickers, start=start, progress=False)
    except Exception as e:
        logger.error(f"Error downloading historical prices for portfolio: {e}")
        return pd.Series(dtype=float)

    # yf.download returns MultiIndex columns when multiple tickers are provided
    # Level 0: 'Open', 'High', 'Low', 'Close', 'Volume', etc.
    # Level 1: ticker symbols
    try:
        if isinstance(data.columns, pd.MultiIndex):
            # Multiple tickers: extract Close prices from MultiIndex
            closes = data.xs("Close", axis=1, level=0)
        elif len(tickers) == 1 and "Close" in data.columns:
            # Single ticker with simple column structure
            closes = data[["Close"]].copy()
            closes.columns = tickers
        else:
            # Fallback: try to extract Close level anyway
            closes = data.xs("Close", axis=1, level=0)
    except (KeyError, AttributeError) as e:
        logger.error(f"Could not extract Close prices from yf.download output: {e}")
        return pd.Series(dtype=float)

    # align column names to tickers
    # ensure each ticker column exists, else fill with NaN
    for t in tickers:
        if t not in closes.columns:
            closes[t] = pd.NA

    # multiply each column by units and sum to get portfolio value per date
        units_map = portfolio_df.set_index("Ticker")["Units"].to_dict()
    # convert closes to numeric
    closes = closes.apply(pd.to_numeric, errors="coerce")

    portfolio_values = pd.Series(0.0, index=closes.index, dtype=float)
    for t in tickers:
        u = units_map.get(t, 0)
        if pd.isna(u) or u is None:
            u = 0
        portfolio_values = portfolio_values.add(closes[t].fillna(0) * float(u), fill_value=0.0)

    portfolio_values.name = "Portfolio Value"
    return portfolio_values


def get_price_data(ticker: str, start="2016-01-01", end=datetime.now()):
    if not isinstance(ticker, str) or ticker.strip() == "":
        raise ValueError("Ticker must be a non-empty string")

    try:
        data = yf.download(ticker, start=start, end=end, progress=False)
    except Exception as e:
        logger.error(f"Error downloading price data for {ticker}: {e}")
        return pd.DataFrame()

    return data

def plot_price_data(df: pd.DataFrame, ticker: str):
    if df.empty:
        logger.warning(f"No data to plot for {ticker}.")
        return

    if "Close" not in df.columns:
        logger.warning(f"Missing 'Close' column for {ticker}. Skipping plot.")
        return

    plt.figure(figsize=(12, 5))
    plt.plot(df['Close'], label=f"{ticker} Close Price")
    plt.title(f"{ticker} Price History")
    plt.xlabel("Date")
    plt.ylabel("Price (USD)")
    plt.legend()
    plt.show()

def get_ticker_year_history(ticker: str):
    """Return 1 year history (close prices) for ticker; empty DataFrame on failure."""
    try:
        hist = yf.download(ticker, period="1y", progress=False)
    except Exception as e:
        logger.error(f"Failed to download 1y history for {ticker}: {e}")
        return pd.DataFrame()
    return hist

def get_ticker_info(ticker: str):
    """
    Try to fetch lightweight info for a ticker (name, marketCap).
    This may not be available for every symbol.
    Return a dict with keys 'shortName' and 'marketCap' (None if missing).
    """
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        name = info.get("shortName") or info.get("longName") or None
        market_cap = info.get("marketCap", None)
        return {"name": name, "marketCap": market_cap}
    except Exception as e:
        logger.debug(f"Ticker.info not available for {ticker}: {e}")
        return {"name": None, "marketCap": None}


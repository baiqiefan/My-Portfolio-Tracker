readme_content = """# My Portfolio Tracker

A simple Python-based portfolio tracker built as a self-project.  
The app reads a portfolio from a CSV file, fetches market data using `yfinance`, calculates portfolio performance, and displays the results through either a command-line interface or a Tkinter desktop GUI.

## Features

- Load portfolio holdings from a CSV file
- Fetch latest stock and crypto price data using Yahoo Finance
- Calculate:
  - Current asset value
  - Total portfolio value
  - Profit / loss
  - Return percentage
  - Asset weight percentage
  - Daily percentage change
  - 52-week high and low
- Display results in a desktop GUI table
- Plot portfolio value over time
- Simple command-line version available

## Project Structure

```text
My-Portfolio-Tracker/
│
├── app.py                  # Tkinter GUI application
├── main.py                 # Command-line version of the tracker
├── portfolio_core.py       # Core portfolio calculation and data-fetching logic
├── portfolio.csv           # Example input portfolio file
├── portfolio_breakdown.csv # Example output / portfolio breakdown data
└── __pycache__/            # Python cache folder

## License

This project is licensed under the MIT License.  
You are free to use, modify, and distribute this project, as long as the original license is included.

This project is provided for learning purposes and comes with no warranty.

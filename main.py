import logging
from portfolio_core import load_portfolio_data, calculate_portfolio_value

def run_cli():
    portfolio = load_portfolio_data()
    details_df, total_value, total_profit = calculate_portfolio_value(portfolio)
    print(details_df)
    print(f"Total Portfolio Value: ${total_value:,.2f}")
    print(f"Total Profit/Loss: ${total_profit:,.2f}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    run_cli()

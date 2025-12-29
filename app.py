import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import logging
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from portfolio_core import load_portfolio_data, calculate_portfolio_value, portfolio_time_series

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

root = tk.Tk()
root.title("Portfolio Tracker")

controls = ttk.Frame(root)
controls.pack(fill = "x", padx = 10, pady = 10)

table_frame = ttk.Frame(root)
table_frame.pack(fill = "both", expand = True, padx = 10, pady = 10)

chart_frame = ttk.Frame(root)
chart_frame.pack(fill = "both", expand = False, padx = 8, pady = 4)

status_frame = ttk.Frame(root)
status_frame.pack(fill = "x", padx = 10, pady = 10)

csv_path = tk.StringVar(value = "portfolio.csv")

ttk.Label(controls, text = "CSV: ").pack(side = "left")
ttk.Entry(controls, textvariable = csv_path, width = 40).pack(side = "left", padx = 4)

def choose_file():
    path = filedialog.askopenfilename(filetypes = [("CSV files", "*.csv"), ("All files", "*.*")])
    if path:
        csv_path.set(path)

ttk.Button(controls, text = "Browse", command = choose_file).pack(side = "left", padx = 4)

status_text = tk.StringVar(value = "Ready")

def set_status(msg):
    status_text.set(msg)

update_btn = ttk.Button(controls, text = "Update")
update_btn.pack(side = "left", padx = 8)
ttk.Label(controls, textvariable = status_text).pack(side = "left", padx = 8)

columns = ("Ticker", "Units", "Current Price", "Value", "Profit", "Return %", "Weight %", "Day %", "52W High", "52W Low")
tree = ttk.Treeview(table_frame, columns = columns, show = "headings", height = 12)
for col in columns:
    tree.heading(col, text = col)
    tree.column(col, width = 100, anchor = "center")
tree.pack(fill = "both", expand = True)

total_value_var = tk.StringVar(value = "Total Value: ")
total_pnl_var = tk.StringVar(value = "Total P/L: ")
ttk.Label(status_frame, textvariable = total_value_var).pack(side = "left", padx = 6)

def render_chart(ts):
    # Remove old chart widgets
    for child in chart_frame.winfo_children():
        child.destroy()
    if ts is None or ts.empty:
        return
    fig = Figure(figsize=(8, 3))
    ax = fig.add_subplot(111)
    ax.plot(ts.index, ts.values, label="Portfolio Value")
    ax.set_title("Portfolio Value Over Time")
    ax.set_xlabel("Date")
    ax.set_ylabel("Value (USD)")
    ax.grid(True)
    ax.legend()
    canvas = FigureCanvasTkAgg(fig, master=chart_frame)
    canvas.draw()
    canvas.get_tk_widget().pack(fill="both", expand=True)


def update_ui (details_df, total_value, total_profit, ts):
    for row_id in tree.get_children():
        tree.delete(row_id)
    for _, r in details_df.iterrows():
        tree.insert("", "end", values = (
            r.get("Ticker", ""),
            r.get("Units", ""),
            r.get("Current Price", ""),
            r.get("Value", ""),
            r.get("Profit", ""),
            r.get("Return %", ""),
            r.get("Weight %", ""),
            r.get("Day %", ""),
            r.get("52W High", ""),
            r.get("52W Low", ""),
        ))
    total_value_var.set(f"Total Value: ${total_value:,.2f}")
    total_pnl_var.set(f"Total P/L: ${total_profit:,.2f}")
    render_chart(ts)
    set_status("Done")
    update_btn.state(["!disabled"])

def worker(path):
    try:
        pf = load_portfolio_data(path)
        details_df, total_value, total_profit = calculate_portfolio_value(pf)
        ts = portfolio_time_series(pf, start = "2016-01-01")
    except Exception as e:
        root.after(0, show_error, str(e))
        return
    root.after(0, update_ui, details_df, total_value, total_profit, ts)

ttk.Label(status_frame, textvariable=total_pnl_var).pack(side="left", padx=6)


def show_error(msg):
    set_status(f"Error: {msg}")
    update_btn.state(["!disabled"])
    messagebox.showerror("Error", msg)

def on_update():
    update_btn.state(["disabled"])
    set_status("Fetching...")
    threading.Thread(target=worker, args=(csv_path.get(),), daemon=True).start()

update_btn.config(command=on_update)

if __name__ =="__main__":
    root.mainloop()

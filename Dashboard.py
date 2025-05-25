import tkinter as tk
from tkinter import messagebox, scrolledtext
from ttkbootstrap import Style
from ttkbootstrap.widgets import Entry, Button, Progressbar, Checkbutton
from ttkbootstrap.constants import *
from zapv2 import ZAPv2
import threading
import time
import csv
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

API_KEY = 'n3m6jha6edpiesf1hbtf7egnhs'
ZAP_PROXY = 'http://127.0.0.1:8080'
zap = ZAPv2(apikey=API_KEY, proxies={'http': ZAP_PROXY, 'https': ZAP_PROXY})
current_theme = "flatly"

def export_results(alerts):
    with open("scan_results.txt", "w", encoding='utf-8') as txt_file, open("scan_results.csv", "w", newline='', encoding='utf-8') as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["Alert", "Risk", "URL", "Description"])
        for alert in alerts:
            if 'xss' in alert['alert'].lower() or 'sql' in alert['alert'].lower():
                txt_file.write(f"[{alert['alert']}]\nRisk: {alert['risk']}\nURL: {alert['url']}\nDescription: {alert['description']}\n\n")
                writer.writerow([alert['alert'], alert['risk'], alert['url'], alert['description']])

def plot_alert_graph(frame, alerts):
    xss_count = sum(1 for alert in alerts if 'xss' in alert['alert'].lower())
    sql_count = sum(1 for alert in alerts if 'sql' in alert['alert'].lower())
    total = len(alerts)

    fig, ax = plt.subplots(figsize=(5, 2.5), dpi=100)
    ax.plot(['XSS', 'SQLi', 'Total'], [xss_count, sql_count, total], marker='o', color='teal')
    ax.set_title("Vulnerability Count")
    ax.set_ylabel("Count")
    ax.grid(True)

    for widget in frame.winfo_children():
        widget.destroy()

    canvas = FigureCanvasTkAgg(fig, master=frame)
    canvas.draw()
    canvas.get_tk_widget().pack()

def scan_url(url, output, progress_bar, graph_frame, stats_labels):
    try:
        zap.urlopen(url)
        time.sleep(2)
        zap.ascan.disable_all_scanners()
        zap.ascan.enable_scanners("40012,40014,40016,40017,40018,40019,40020,40021")

        output.insert(tk.END, "🔍 Starting active scan (XSS + SQL Injection only)...\n")
        scan_id = zap.ascan.scan(url)

        start_time = time.time()
        timeout = 300
        last_progress = -1

        while True:
            progress = int(zap.ascan.status(scan_id))
            if progress != last_progress:
                output.insert(tk.END, f"⏳ Scan progress: {progress}%\n")
                progress_bar['value'] = progress
                output.see(tk.END)
                last_progress = progress
            if progress >= 100:
                break
            if time.time() - start_time > timeout:
                output.insert(tk.END, "\n⏰ Scan timed out after 5 minutes.\n")
                return
            time.sleep(3)

        output.insert(tk.END, "✅ Scan complete! Fetching alerts...\n")
        alerts = zap.core.alerts(baseurl=url)

        found = False
        xss_count = 0
        sql_count = 0
        for alert in alerts:
            if 'xss' in alert['alert'].lower() or 'sql' in alert['alert'].lower():
                found = True
                output.insert(tk.END, f"🚨 [{alert['alert']}]\nRisk: {alert['risk']}\nURL: {alert['url']}\nDescription: {alert['description']}\n\n")
                if 'xss' in alert['alert'].lower():
                    xss_count += 1
                if 'sql' in alert['alert'].lower():
                    sql_count += 1

        if not found:
            output.insert(tk.END, "✔️ No XSS or SQL Injection vulnerabilities found.\n")

        export_results(alerts)
        output.insert(tk.END, "📁 Results saved to scan_results.txt and scan_results.csv\n")

        # Update stats and graph
        stats_labels["xss"].config(text=f"XSS Alerts: {xss_count}")
        stats_labels["sql"].config(text=f"SQLi Alerts: {sql_count}")
        stats_labels["total"].config(text=f"Total Alerts: {len(alerts)}")
        plot_alert_graph(graph_frame, alerts)

    except Exception as e:
        messagebox.showerror("Scan Error", str(e))

def start_scan(entry, output, progress_bar, graph_frame, stats_labels):
    url = entry.get().strip()
    if not url.startswith("http"):
        messagebox.showwarning("Invalid URL", "URL must start with http:// or https://")
        return
    output.delete("1.0", tk.END)
    progress_bar['value'] = 0
    threading.Thread(target=scan_url, args=(url, output, progress_bar, graph_frame, stats_labels), daemon=True).start()

def toggle_theme(style, toggle_btn):
    global current_theme
    current_theme = "darkly" if current_theme == "flatly" else "flatly"
    style.theme_use(current_theme)
    toggle_btn.config(text="🌙 Dark Mode" if current_theme == "flatly" else "☀️ Light Mode")

def main_gui():
    style = Style(theme=current_theme)
    try:
        root = style.master
        root.title("🛡️ CYBERSECURITY DASHBOARD FOR WEB THREATS")
        root.geometry("1000x650")
        root.minsize(800, 600)
    except tk.TclError as e:
        print("GUI could not be initialized:", e)
        return

    # Layout
    root.columnconfigure(1, weight=3)
    root.rowconfigure(0, weight=1)

    # Sidebar
    sidebar = tk.Frame(root, bg=style.colors.bg)
    sidebar.grid(row=0, column=0, sticky="ns", padx=10, pady=10)

    tk.Label(sidebar, text="🔗 Website URL", font=("Segoe UI", 11), bg=style.colors.bg).pack(anchor="w", pady=(10, 2))

    url_entry = Entry(sidebar, width=30)
    url_entry.pack(pady=5)

    progress_bar = Progressbar(sidebar, bootstyle="info-striped", length=200)
    progress_bar.pack(pady=10)

    scan_btn = Button(sidebar, text="🔍 Start Scan", bootstyle=SUCCESS, width=20,
                      command=lambda: start_scan(url_entry, output_box, progress_bar, graph_frame, stats_labels))
    scan_btn.pack(pady=5)

    exit_btn = Button(sidebar, text="❌ Exit", bootstyle=DANGER, width=20, command=root.destroy)
    exit_btn.pack(pady=5)

    toggle_btn = Checkbutton(sidebar, text="🌙 Dark Mode", command=lambda: toggle_theme(style, toggle_btn))
    toggle_btn.pack(pady=5)

    # Main Content
    content_frame = tk.Frame(root)
    content_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
    content_frame.columnconfigure(0, weight=1)
    content_frame.rowconfigure(1, weight=1)

    # Stats Display
    stats_frame = tk.Frame(content_frame)
    stats_frame.grid(row=0, column=0, sticky="ew", pady=5)
    stats_labels = {
        "xss": tk.Label(stats_frame, text="XSS Alerts: 0", font=("Segoe UI", 10)),
        "sql": tk.Label(stats_frame, text="SQLi Alerts: 0", font=("Segoe UI", 10)),
        "total": tk.Label(stats_frame, text="Total Alerts: 0", font=("Segoe UI", 10)),
    }
    for lbl in stats_labels.values():
        lbl.pack(side=tk.LEFT, padx=15)

    # Output Box
    output_box = scrolledtext.ScrolledText(content_frame, height=15, font=("Consolas", 10))
    output_box.grid(row=1, column=0, sticky="nsew")

    # Graph Frame
    graph_frame = tk.Frame(content_frame)
    graph_frame.grid(row=2, column=0, sticky="ew", pady=10)

    root.mainloop()

if __name__ == "__main__":
    main_gui()

# ===================================================================================
# Project: KickerzViews
# Version: 8.1 (No-Proxy Edition)
# Description: A high-performance, purely asynchronous script using a single-browser,
#              multi-context model. This version makes direct connections without proxies.
#              The UI is a summary-based dashboard.
#
# Disclaimer: This script is intended for educational and research purposes only.
# The developer is not responsible for any misuse of this software.
# By using this script, you agree to use it legally and ethically.
# ===================================================================================

import asyncio
import time
import re
import random
import datetime
import threading
from collections import Counter

try:
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.console import Console
    from rich.text import Text
except ImportError:
    print("Error: The 'rich' library is required for the UI.")
    print("Please install it by running: pip install rich")
    exit(1)

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- CONFIGURATION ---
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
MAX_RETRIES = 3
NAVIGATION_TIMEOUT = 90000
LOOP_DELAY_SECONDS = (30, 60)

# --- GLOBAL STATE & UI MANAGEMENT ---
state_lock = threading.Lock()
thread_states = {}
successful_visits = 0
failed_visits = 0
start_time = datetime.datetime.now()
console = Console()

# --- BROWSER MANAGER ---
class BrowserManager:
    """Manages ONE single, shared browser instance for maximum efficiency."""
    def __init__(self, playwright_instance):
        self.browser = None
        self._playwright = playwright_instance

    async def launch(self):
        """Launches the browser without any proxy settings."""
        self.browser = await self._playwright.chromium.launch(headless=True)

    async def new_context(self):
        """Creates a brand new, 100% isolated browser context."""
        return await self.browser.new_context(ignore_https_errors=True, user_agent=USER_AGENT)

    async def close(self):
        if self.browser:
            await self.browser.close()

# --- DYNAMIC LIVE UI THREAD ---
def rich_dashboard_thread(stop_event: threading.Event):
    """Renders the summary-based UI in a separate thread."""
    def generate_layout() -> Panel:
        with state_lock:
            perf_table = Table.grid(expand=True, padding=(0, 1))
            perf_table.add_column(ratio=1); perf_table.add_column(ratio=1)
            elapsed_time = datetime.datetime.now() - start_time
            total_seconds = elapsed_time.total_seconds()
            vpm = (successful_visits / (total_seconds / 60)) if total_seconds > 0 else 0
            
            perf_table.add_row(
                Text(f"🟢 Successful Visits: {successful_visits}", style="bold green"),
                Text(f" Elapsed Time: {str(elapsed_time).split('.')[0]}", style="cyan")
            )
            perf_table.add_row(
                Text(f"🔴 Failed Visits: {failed_visits}", style="bold red"),
                Text(f" Visits/Min (VPM): {vpm:.2f}", style="magenta")
            )
            
            status_counts = Counter(thread_states.values())
            summary_table = Table.grid(expand=True)
            summary_table.add_column()
            summary_table.add_row(Text(f"⚡ Navigating: {status_counts.get('Navigating', 0)}", style="cyan"))
            summary_table.add_row(Text(f"🎬 On Page:    {status_counts.get('On Page', 0)}", style="magenta"))
            summary_table.add_row(Text(f"⏳ Waiting:    {status_counts.get('Waiting', 0)}", style="yellow"))
            summary_table.add_row(Text(f"❌ Failed:     {status_counts.get('Failed', 0)}", style="red"))

        performance_panel = Panel(perf_table, title="[bold yellow]Overall Performance[/bold yellow]", border_style="yellow")
        summary_panel = Panel(summary_table, title="[bold blue]Thread State Summary[/bold blue]", border_style="blue")
        footer = Text("Developer: kia6666@rit.edu | For Educational & Research Purposes Only.", justify="center", style="dim")
        
        main_grid = Table.grid(expand=True, padding=1)
        main_grid.add_row(performance_panel); main_grid.add_row(summary_panel); main_grid.add_row(footer)
        return Panel(main_grid, title="[bold green]🚀 KickerzViews Live Dashboard[/bold green]", border_style="green")

    with Live(generate_layout(), console=console, screen=True, auto_refresh=False, vertical_overflow="visible") as live:
        while not stop_event.is_set():
            live.update(generate_layout(), refresh=True)
            time.sleep(1)

# --- ASYNCHRONOUS WORKER LOGIC ---
def update_thread_state(worker_id: int, status: str):
    """Thread-safe function to update a worker's status for the UI summary."""
    with state_lock:
        thread_states[worker_id] = status

async def visit_website_headless(manager: BrowserManager, target_url: str, visit_duration: int, worker_id: int):
    """Performs a single, completely isolated visit by creating and destroying a context."""
    global successful_visits, failed_visits
    context = None
    try:
        context = await manager.new_context()
        page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        await page.route(re.compile(r"\.(jpg|jpeg|png|gif|css|woff|woff2)$"), lambda route: route.abort())

        for attempt in range(1, MAX_RETRIES + 1):
            update_thread_state(worker_id, "Navigating")
            try:
                await page.goto(target_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
                update_thread_state(worker_id, "On Page")
                await asyncio.sleep(visit_duration)
                with state_lock: successful_visits += 1
                update_thread_state(worker_id, None)
                return
            except Exception:
                if attempt == MAX_RETRIES:
                    with state_lock: failed_visits += 1
                    update_thread_state(worker_id, "Failed")
    finally:
        if context:
            await context.close()

async def worker_loop(manager: BrowserManager, target_url: str, visit_duration: int, worker_id: int):
    """The main asynchronous loop for each worker task."""
    while True:
        try:
            await visit_website_headless(manager, target_url, visit_duration, worker_id)
            delay = random.randint(*LOOP_DELAY_SECONDS)
            update_thread_state(worker_id, "Waiting")
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break
        except Exception:
            update_thread_state(worker_id, "Failed")
            await asyncio.sleep(30)

# --- MAIN ASYNC EXECUTION BLOCK ---
async def main(total_workers: int, url: str, duration: int):
    """Initializes the single manager and runs all workers as asyncio tasks."""
    console.print(f"\n[bold green]Initializing KickerzViews...[/]")
    console.print(f"Total Workers Requested: [bold cyan]{total_workers}[/]")
    console.print(f"Mode: [bold magenta]Direct Connection (No Proxies)[/]")
    
    stop_ui_event = threading.Event()
    ui_thread = threading.Thread(target=rich_dashboard_thread, args=(stop_ui_event,), daemon=True)
    ui_thread.start()
    
    async with async_playwright() as p:
        manager = BrowserManager(p)
        await manager.launch()
        
        tasks = []
        try:
            for i in range(1, total_workers + 1):
                update_thread_state(i, "Waiting")
                task = asyncio.create_task(worker_loop(manager, url, duration, i))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            console.print("\n[bold yellow]Cancellation signal received...", style="yellow")
        finally:
            console.print("[bold yellow]Closing shared browser instance...", style="yellow")
            await manager.close()
            stop_ui_event.set()

if __name__ == "__main__":
    try:
        url_input = input("Enter the full URL to visit: ").strip()
        worker_count_input = int(input(f"Enter total number of concurrent workers (e.g., 20000): ").strip())
        duration_input = int(input("Enter visit duration in seconds (on-page time): ").strip())

        asyncio.run(main(worker_count_input, url_input, duration_input))

    except ValueError:
        console.print("\n[bold red]Error:[/] Invalid input. Please enter numbers.", style="red")
    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]Keyboard interrupt detected. Shutting down gracefully...", style="yellow")
    finally:
        console.print("[bold green]KickerzViews has terminated.", style="green")
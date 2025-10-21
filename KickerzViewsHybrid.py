# ===================================================================================
# Project: KickerzViews
# Version: 16.0 (Uncapped Hybrid - v8.1 Core)
# Description: The definitive script built on the user-preferred pure async, uncapped
#              architecture. Integrates all advanced features including hybrid mode,
#              URL rotation, and optional human-like actions.
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
import logging
from collections import Counter

try:
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.console import Console
    from rich.text import Text
except ImportError:
    print("Error: The 'rich' library is required for the UI. Please run: pip install rich")
    exit(1)

from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError

# --- CONFIGURATION ---
PROXY_TOKEN = "YOUR_PROXY_TOKEN"
PROXY_SERVER = "YOUR_PROXY_SERVER_ADDRESS:PORT"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
COMMON_VIEWPORTS = [
    {"width": 1920, "height": 1080}, {"width": 1536, "height": 864},
    {"width": 1440, "height": 900}, {"width": 1366, "height": 768},
]

# --- Resilience & Looping ---
MAX_RETRIES = 3
NAVIGATION_TIMEOUT = 90000
LOOP_DELAY_SECONDS = (30, 60)

# --- GLOBAL STATE ---
state_lock = threading.Lock(); thread_states = {}; worker_types = {}
successful_visits = 0; failed_visits = 0; start_time = datetime.datetime.now()
console = Console()

# --- Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s', filename='kickerzviews.log', filemode='w')

# --- BROWSER MANAGER ---
class BrowserManager:
    """Manages ONE single, shared browser instance, with or without a proxy."""
    def __init__(self, playwright_instance, proxy_config=None):
        self.browser = None
        self._playwright = playwright_instance
        self._proxy_config = proxy_config

    async def launch(self):
        self.browser = await self._playwright.chromium.launch(headless=True, proxy=self._proxy_config)

    async def new_context(self):
        """Creates a brand new, 100% isolated browser context with a random viewport."""
        viewport = random.choice(COMMON_VIEWPORTS)
        return await self.browser.new_context(
            ignore_https_errors=True, user_agent=USER_AGENT, viewport=viewport
        )

    async def close(self):
        if self.browser: await self.browser.close()

# --- DYNAMIC LIVE UI THREAD ---
def rich_dashboard_thread(stop_event: threading.Event, run_mode: str, total_workers: int, proxy_workers: int):
    """Renders the summary-based UI in a separate thread."""
    def generate_layout() -> Panel:
        with state_lock:
            perf_table = Table.grid(expand=True, padding=(0, 1))
            perf_table.add_column(ratio=1); perf_table.add_column(ratio=1)
            elapsed_time = datetime.datetime.now() - start_time
            total_seconds = max(1, elapsed_time.total_seconds())
            vpm = (successful_visits / (total_seconds / 60))
            perf_table.add_row(
                Text(f"🟢 Successful Visits: {successful_visits}", style="bold green"),
                Text(f"🕒 Elapsed Time: {str(elapsed_time).split('.')[0]}", style="cyan")
            )
            perf_table.add_row(
                Text(f"🔴 Failed Visits: {failed_visits}", style="bold red"),
                Text(f"🚀 Visits/Min (VPM): {vpm:.2f}", style="magenta")
            )

            config_table = Table.grid(expand=True)
            config_table.add_row(f"Mode: [bold red]{run_mode}[/]")
            config_table.add_row(f"Total Workers: [bold cyan]{total_workers}[/]")
            if "Proxy" in run_mode:
                config_table.add_row(f"  - Proxy: [blue]{proxy_workers}[/] | Direct: [blue]{total_workers - proxy_workers}[/]")

            status_counts = Counter(thread_states.values())
            summary_table = Table.grid(expand=True)
            summary_table.add_row(Text(f"⚡ Navigating: {status_counts.get('Navigating', 0)}", style="cyan"))
            summary_table.add_row(Text(f"🎬 On Page:    {status_counts.get('On Page', 0)}", style="magenta"))
            summary_table.add_row(Text(f"⏳ In Delay Period:   {status_counts.get('Waiting', 0)}", style="yellow"))
            summary_table.add_row(Text(f"❌ Failed / Ended:  {status_counts.get('Failed', 0)}", style="red"))

        performance_panel = Panel(perf_table, title="[yellow]Performance[/]", border_style="yellow")
        config_panel = Panel(config_table, title="[yellow]Configuration[/]", border_style="yellow")
        summary_panel = Panel(summary_table, title="[blue]Worker Summary[/]", border_style="blue")
        footer = Text("Developer: kia6666@rit.edu | For Educational & Research Purposes Only.", justify="center", style="dim")
        
        main_grid = Table.grid(expand=True, padding=1)
        main_grid.add_row(config_panel); main_grid.add_row(performance_panel)
        main_grid.add_row(summary_panel); main_grid.add_row(footer)
        return Panel(main_grid, title="[bold red]🚀 KickerzViews [UNCAPPED MODE][/]")

    with Live(generate_layout(), console=console, screen=True, auto_refresh=False) as live:
        while not stop_event.is_set():
            live.update(generate_layout(), refresh=True); time.sleep(1)

# --- WORKER LOGIC ---
def update_thread_state(worker_id: int, status: str):
    with state_lock: thread_states[worker_id] = status

async def perform_human_like_actions(page):
    """Simulates realistic user interactions on the page."""
    try:
        for _ in range(random.randint(2, 4)):
            await page.mouse.move(random.randint(100, page.viewport_size['width'] - 100), random.randint(100, page.viewport_size['height'] - 100), steps=random.randint(5, 10))
            await asyncio.sleep(random.uniform(0.2, 0.5))
        for _ in range(random.randint(1, 3)):
            await page.mouse.wheel(0, random.randint(200, 1000)); await asyncio.sleep(random.uniform(0.5, 1.5))
    except Exception as e:
        logging.warning(f"Worker could not perform human-like actions: {e}")

async def visit_website_headless(manager: BrowserManager, target_url: str, visit_duration: int, worker_id: int, use_advanced_actions: bool):
    """Performs a single, completely isolated visit."""
    global successful_visits, failed_visits
    context = None
    try:
        context = await manager.new_context(); page = await context.new_page()
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        await page.route(re.compile(r"\.(jpg|jpeg|png|gif|css|woff|woff2)$"), lambda r: r.abort())
        for _ in range(MAX_RETRIES):
            try:
                update_thread_state(worker_id, "Navigating")
                await page.goto(target_url, wait_until="domcontentloaded", timeout=NAVIGATION_TIMEOUT)
                update_thread_state(worker_id, "On Page")
                if use_advanced_actions:
                    await perform_human_like_actions(page)
                await asyncio.sleep(visit_duration)
                with state_lock: successful_visits += 1
                logging.info(f"Worker-{worker_id} successfully viewed {target_url}")
                update_thread_state(worker_id, None)
                return
            except Exception:
                continue
        with state_lock: failed_visits += 1
        update_thread_state(worker_id, "Failed")
        logging.error(f"Worker-{worker_id} failed to view {target_url} after {MAX_RETRIES} retries.")
    finally:
        if context: await context.close()

async def worker_loop(manager: BrowserManager, url_list: list, visit_duration: int, worker_id: int, use_advanced_actions: bool):
    """The main asynchronous loop for each worker task, based on the v8.1 engine."""
    while True:
        try:
            target_url = random.choice(url_list)
            await visit_website_headless(manager, target_url, visit_duration, worker_id, use_advanced_actions)
            delay = random.randint(*LOOP_DELAY_SECONDS)
            update_thread_state(worker_id, "Waiting")
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            break
        except Exception as e:
            update_thread_state(worker_id, "Failed")
            logging.error(f"Critical error in Worker-{worker_id} loop: {e}")
            await asyncio.sleep(30)

async def check_proxy(proxy_config):
    console.print("\n[yellow]Performing proxy health check...[/]")
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, proxy=proxy_config); page = await browser.new_page(ignore_https_errors=True)
            await page.goto("https://api.ipify.org", timeout=20000); await browser.close()
        console.print("[bold green]✅ Proxy health check PASSED.[/]"); return True
    except Exception:
        console.print("[bold red]❌ Proxy health check FAILED.[/]"); return False

# --- MAIN ASYNC EXECUTION BLOCK (v8.1 STYLE) ---
async def main(proxy_workers: int, direct_workers: int, urls: list, duration: int, run_mode: str, advanced_actions: bool):
    """Initializes managers and runs ALL workers as concurrent asyncio tasks."""
    proxy_config = {"server": PROXY_SERVER, "username": PROXY_TOKEN}
    total_workers = proxy_workers + direct_workers
    
    stop_ui_event = threading.Event()
    ui_thread = threading.Thread(target=rich_dashboard_thread, args=(stop_ui_event, run_mode, total_workers, proxy_workers), daemon=True)
    ui_thread.start()
    
    async with async_playwright() as p:
        proxy_manager = None; direct_manager = None
        try:
            if proxy_workers > 0:
                proxy_manager = BrowserManager(p, proxy_config); await proxy_manager.launch()
            if direct_workers > 0:
                direct_manager = BrowserManager(p); await direct_manager.launch()

            tasks = []
            # Create all tasks and add them to the list
            for i in range(1, proxy_workers + 1):
                worker_types[i] = 'Proxy'
                tasks.append(asyncio.create_task(worker_loop(proxy_manager, urls, duration, i, advanced_actions)))
            for i in range(proxy_workers + 1, total_workers + 1):
                worker_types[i] = 'Direct'
                tasks.append(asyncio.create_task(worker_loop(direct_manager, urls, duration, i, advanced_actions)))
            
            # Unleash all tasks at once
            await asyncio.gather(*tasks)

        except asyncio.CancelledError:
            console.print("\n[yellow]Cancellation signal received...[/]")
        finally:
            console.print("[yellow]Closing browser managers...[/]")
            if proxy_manager: await proxy_manager.close()
            if direct_manager: await direct_manager.close()
            stop_ui_event.set()

if __name__ == "__main__":
    try:
        console.print("[bold green]--- KickerzViews Configuration ---[/]")
        console.print("[bold red]WARNING: Running in UNLIMITED CONCURRENCY mode.[/]")
        
        url_input = console.input("[bold]Enter URL or comma-separated URLs: [/]").strip()
        urls_to_visit = [url.strip() for url in url_input.split(',')]
        duration_input = int(console.input("[bold]Enter visit duration (seconds): [/]").strip())

        adv_choice = console.input("\n[bold]Enable advanced human-like actions? (y/n): [/]").strip().lower()
        advanced_actions_enabled = True if adv_choice == 'y' else False

        console.print("\n[bold]Select Mode:[/]\n  [cyan]1.[/] Proxies\n  [cyan]2.[/] Direct\n  [cyan]3.[/] Hybrid")
        mode_choice = console.input("> ").strip()

        proxy_w, direct_w, run_mode_str = 0, 0, ""
        if mode_choice == '1':
            run_mode_str = "Proxy (Uncapped)"; proxy_w = int(console.input("Total number of [blue]proxy[/] workers: ").strip())
        elif mode_choice == '2':
            run_mode_str = "Direct (Uncapped)"; direct_w = int(console.input("Total number of [blue]direct[/] workers: ").strip())
        elif mode_choice == '3':
            run_mode_str = "Hybrid (Uncapped)";
            proxy_w = int(console.input("Number of [blue]proxy[/] workers: ").strip())
            direct_w = int(console.input("Number of [blue]direct[/] workers: ").strip())
        else: raise ValueError("Invalid mode selected.")

        if proxy_w > 0 and not asyncio.run(check_proxy({"server": PROXY_SERVER, "username": PROXY_TOKEN})):
            exit(1)
        
        logging.info(f"Start: Mode={run_mode_str}, Proxies={proxy_w}, Direct={direct_w}, Adv={advanced_actions_enabled}, URLs={urls_to_visit}")
        console.print("\n[bold green]Configuration complete. Starting KickerzViews...[/]"); time.sleep(2)
        asyncio.run(main(proxy_w, direct_w, urls_to_visit, duration_input, run_mode_str, advanced_actions_enabled))

    except (ValueError, TypeError): console.print(f"\n[red]Error: Invalid input.[/]")
    except KeyboardInterrupt: console.print("\n\n[yellow]Keyboard interrupt. Shutting down...[/]")
    finally:
        logging.info("KickerzViews session terminated.")
        console.print("[bold green]KickerzViews has terminated.", style="green")
# ===================================================================================
# Project: Kickerz
# Developer: kia6666@rit.edu
#
# Disclaimer: This script is intended for educational and research purposes only.
# The developer is not responsible for any misuse of this software.
# By using this script, you agree to use it legally and ethically.
# ===================================================================================

import sys
import time
import random
import datetime
import asyncio
import websockets
import json
import os
from threading import Thread
from concurrent.futures import ThreadPoolExecutor
import tls_client

try:
    from rich.live import Live
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress, BarColumn, TextColumn
    from rich.console import Console
    from rich.text import Text
    from rich.align import Align
except ImportError:
    print("Error: The 'rich' library is required for the new UI.")
    print("Please install it by running: pip install rich")
    sys.exit(1)


# --- YOUR ORIGINAL CONFIG AND GLOBAL STATE ---
CLIENT_TOKEN = "e1393935a959b4020a4491574f6490129f678acdaa92760471263db43487f823"

# Global state
channel = ""
channel_id = None
stream_id = None
stop = False
start_time = None
connections = 0
target_connections = 0 # Added for dashboard
attempts = 0
pings = 0
heartbeats = 0
viewers = 0
last_check = 0
num_stable_workers = 0
num_churn_workers = 0
token_fails = 0 # New stat for fault tolerance

executor = ThreadPoolExecutor(max_workers=750)
console = Console()

# --- YOUR ORIGINAL, WORKING FUNCTIONS ---

def clean_channel_name(name):
    if "kick.com/" in name:
        parts = name.split("kick.com/")
        return parts[1].split("/")[0].split("?")[0].lower()
    return name.lower()

def get_channel_info(name):
    global channel_id, stream_id
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        s.headers.update({
            'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        })
        response = s.get(f'https://kick.com/api/v2/channels/{name}', timeout_seconds=10)
        if response.status_code == 200:
            data = response.json()
            channel_id = data.get("id")
            if 'livestream' in data and data['livestream']:
                stream_id = data['livestream'].get('id')
            return True
        return None
    except Exception as e:
        console.print(f"[bold red]Error in get_channel_info:[/] {e}")
        return None

def get_token():
    global token_fails
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        s.get("https://kick.com/", headers={'Accept-Language': 'en-US,en;q=0.9'})
        token_headers = {
            'Accept': 'application/json, text/plain, */*', 'Accept-Language': 'en-US,en;q=0.9',
            'X-Client-Token': CLIENT_TOKEN, 'Referer': 'https://kick.com/', 'Origin': 'https://kick.com',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        response = s.get('https://websockets.kick.com/viewer/v1/token', headers=token_headers, timeout_seconds=10)
        if response.status_code == 200:
            token = response.json().get("data", {}).get("token")
            if token: return token
        token_fails += 1
        return None
    except:
        token_fails += 1
        return None

def get_viewer_count():
    global viewers, last_check
    if not stream_id: return
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        s.headers.update({'Accept': 'application/json, text/plain, */*'})
        url = f"https://kick.com/current-viewers?ids[]={stream_id}"
        response = s.get(url, timeout_seconds=10)
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                viewers = data[0].get('viewers', 0)
                last_check = time.time()
    except:
        pass

# --- NEW 'RICH' DASHBOARD FUNCTION (REPLACES show_stats) ---

def rich_dashboard_thread():
    def generate_layout():
        status_text = Text("RUNNING", style="bold green")
        header = Text.assemble(
            "Channel: ", (f"🦎 {channel}", "bold cyan"), "    Status: ", status_text,
            justify="center"
        )
        health_table = Table(box=None, expand=True, show_header=True, header_style="bold magenta")
        for col in ["Connections", "Attempts", "Pings", "Heartbeats", "Token Fails"]:
            health_table.add_column(col, justify="center")
        health_table.add_row(
            f"[green]{connections:,}[/green] / {target_connections:,}", f"[yellow]{attempts:,}[/yellow]",
            f"[cyan]{pings:,}[/cyan]", f"[magenta]{heartbeats:,}[/magenta]",
            f"[bold red]{token_fails:,}[/bold red]"
        )
        stream_table = Table(box=None, expand=True, show_header=True, header_style="bold magenta")
        stream_table.add_column("Live Viewers", justify="center")
        stream_table.add_column("Worker Types (S/C)", justify="center")
        stream_table.add_row(f"[bold cyan]{viewers:,}[/bold cyan]", f"[bold blue]{num_stable_workers} / {num_churn_workers}[/bold blue]")
        
        progress = Progress(TextColumn("[bold blue]Connections[/bold blue]"), BarColumn(),"[progress.percentage]{task.percentage:>3.0f}%", expand=True)
        progress.add_task("connections", total=target_connections, completed=connections)
        
        duration = (datetime.datetime.now() - start_time) if start_time else datetime.timedelta(0)
        duration_seconds = duration.total_seconds()
        cps = (attempts / duration_seconds) if duration_seconds > 0 else 0.0

        perf_table = Table(box=None, expand=True, show_header=False)
        perf_table.add_column("Elapsed")
        perf_table.add_column("CPS", justify="right")
        perf_table.add_row(f"Elapsed: {str(duration).split('.')[0]}", f"Avg. Attempts/Sec: {cps:.2f}")

        footer = Text("Developer: kia6666@rit.edu | For Educational & Research Purposes Only.", style="dim", justify="center")
        
        performance_grid = Table.grid(expand=True); performance_grid.add_row(progress); performance_grid.add_row(perf_table)
        
        main_grid = Table.grid(padding=1, expand=True)
        main_grid.add_row(Panel(header, title="[bold blue]Kickerz Live Dashboard[/bold blue]", border_style="blue"))
        main_grid.add_row(Panel(health_table, title="[bold yellow]Bot Health[/bold yellow]", border_style="yellow"))
        main_grid.add_row(Panel(stream_table, title="[bold yellow]Stream Info[/bold yellow]", border_style="yellow"))
        main_grid.add_row(Panel(performance_grid, title="[bold yellow]Performance[/bold yellow]", border_style="yellow"))
        main_grid.add_row(footer)
        
        return Align.center(main_grid)

    with Live(generate_layout(), console=console, screen=True, auto_refresh=False, vertical_overflow="visible") as live:
        while not stop:
            if time.time() - last_check >= 2:
                get_viewer_count()
            live.update(generate_layout(), refresh=True)
            time.sleep(1)

# --- YOUR FAULT-TOLERANT WORKER LOGIC (UNCHANGED) ---

async def websocket_lifecycle(token):
    global connections, heartbeats, pings
    connected = False
    try:
        url = f"wss://websockets.kick.com/viewer/v1/connect?token={token}"
        async with websockets.connect(url, open_timeout=5, close_timeout=5) as ws:
            connections += 1
            connected = True
            await ws.send(json.dumps({"type": "channel_handshake", "data": {"message": {"channelId": channel_id}}}))
            heartbeats += 1
            while not stop:
                await ws.send(json.dumps({"type": "ping"}))
                pings += 1
                await asyncio.sleep(12 + random.uniform(1, 5))
    except (websockets.exceptions.WebSocketException, asyncio.TimeoutError, OSError):
        pass
    finally:
        if connected and connections > 0:
            connections -= 1

async def worker(worker_type="stable"):
    global attempts
    loop = asyncio.get_running_loop()
    retry_delay = 5
    while not stop:
        attempts += 1
        token = await loop.run_in_executor(executor, get_token)
        if token:
            retry_delay = 5
            if worker_type == "stable":
                await websocket_lifecycle(token)
                await asyncio.sleep(random.uniform(1, 3))
            elif worker_type == "churn":
                try:
                    await asyncio.wait_for(websocket_lifecycle(token), timeout=random.uniform(45, 300))
                except asyncio.TimeoutError:
                    pass
                await asyncio.sleep(random.uniform(10, 60))
        else:
            await asyncio.sleep(retry_delay)
            retry_delay = min(retry_delay * 2, 60) # Exponential backoff

async def supervisor(worker_type):
    while not stop:
        try:
            await worker(worker_type)
        except asyncio.CancelledError:
            break
        except Exception as e:
            console.log(f"[bold red]SUPERVISOR caught an unhandled exception: {e}. Restarting worker...[/bold red]")
            await asyncio.sleep(5)

# --- YOUR ORIGINAL MAIN AND RUN FUNCTIONS (ADAPTED FOR DASHBOARD) ---

async def main_async(total_connections, stable_percentage):
    global num_stable_workers, num_churn_workers
    num_stable_workers = int(total_connections * (stable_percentage / 100))
    num_churn_workers = total_connections - num_stable_workers
    
    console.print(f"\n[green]Deploying {total_connections} connections:[/green]")
    console.print(f"  - [bold blue]{num_stable_workers} STABLE[/bold blue] supervisors")
    console.print(f"  - [bold magenta]{num_churn_workers} CHURN[/bold magenta] supervisors")
    
    tasks = [asyncio.create_task(supervisor("stable")) for _ in range(num_stable_workers)]
    tasks.extend([asyncio.create_task(supervisor("churn")) for _ in range(num_churn_workers)])
    
    await asyncio.gather(*tasks, return_exceptions=False)

def run(total_connections, channel_name, stable_percentage):
    global channel, start_time, channel_id, stream_id, stop, target_connections
    channel = clean_channel_name(channel_name)
    start_time = datetime.datetime.now()
    target_connections = total_connections
    
    with console.status("[bold green]Initializing...[/bold green]"):
        if not get_channel_info(channel) or not stream_id:
            console.print("\n[bold red][FATAL][/bold red] Could not get channel info or stream ID. Channel is likely OFFLINE.")
            return
        console.print(f"[green]✓ Channel Info Fetched[/green]")

    # Start the dedicated, reliable UI thread
    stats_thread = Thread(target=rich_dashboard_thread, daemon=True)
    stats_thread.start()
    
    try:
        asyncio.run(main_async(total_connections, stable_percentage))
    except (KeyboardInterrupt, asyncio.CancelledError):
        pass
    finally:
        stop = True

if __name__ == "__main__":
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
        channel_input = input("Enter channel name or URL: ").strip()
        thread_input = int(input("Enter TOTAL number of connections: ").strip())
        stable_perc_input = int(input("Enter percentage of STABLE connections (e.g., 70): ").strip())
        if not (0 <= stable_perc_input <= 100): raise ValueError("Percentage must be 0-100")
        
        run(thread_input, channel_input, stable_perc_input)

    except ValueError as e:
        console.print(f"\n[bold red]Invalid input:[/bold red] {e}")
    except KeyboardInterrupt:
        pass
    finally:
        stop = True
        console.print("\n[yellow]Script terminated.[/yellow]")
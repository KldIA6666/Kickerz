# = a==================================================================================
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
from threading import Thread, Lock
from collections import deque
import tls_client
from concurrent.futures import ThreadPoolExecutor

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
max_connections = 0
target_token_pool = 0
stop = False
start_time = None
connections = 0
attempts = 0
pings = 0
heartbeats = 0
viewers = 0
last_check = 0
token_queue = deque()
token_lock = Lock()
connections_started = False
token_fails = 0

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
        # *** THIS IS THE CORRECTED PART: Using Text.assemble() to build styled text ***
        status_text = Text("RUNNING", style="bold green") if connections_started else Text("BUILDING TOKENS", style="bold yellow")
        header = Text.assemble(
            "Channel: ", (f"🦎 {channel}", "bold cyan"), "    Status: ", status_text,
            justify="center"
        )

        with token_lock: token_count = len(token_queue)
        
        health_table = Table(box=None, expand=True, show_header=True, header_style="bold magenta")
        for col in ["Connections", "Attempts", "Pings", "Heartbeats", "Token Fails"]:
            health_table.add_column(col, justify="center")
        health_table.add_row(
            f"[green]{connections:,}[/green] / {max_connections:,}", f"[yellow]{attempts:,}[/yellow]",
            f"[cyan]{pings:,}[/cyan]", f"[magenta]{heartbeats:,}[/magenta]",
            f"[bold red]{token_fails:,}[/bold red]"
        )
        stream_table = Table(box=None, expand=True, show_header=True, header_style="bold magenta")
        stream_table.add_column("Live Viewers", justify="center")
        stream_table.add_column("Token Pool", justify="center")
        stream_table.add_row(f"[bold cyan]{viewers:,}[/bold cyan]", f"[bold blue]{token_count:,} / {target_token_pool:,}[/bold blue]")
        
        progress = Progress(TextColumn("[bold blue]Token Pool[/bold blue]"), BarColumn(),"[progress.percentage]{task.percentage:>3.0f}%", expand=True)
        progress.add_task("tokens", total=target_token_pool or 1, completed=token_count)
        
        duration = (datetime.datetime.now() - start_time) if start_time else datetime.timedelta(0)
        footer = Text("Developer: kia6666@rit.edu | For Educational & Research Purposes Only.", style="dim", justify="center")
        
        main_grid = Table.grid(padding=1, expand=True)
        main_grid.add_row(Panel(header, title="[bold blue]Kickerz Live Dashboard[/bold blue]", border_style="blue"))
        main_grid.add_row(Panel(health_table, title="[bold yellow]Bot Health[/bold yellow]", border_style="yellow"))
        main_grid.add_row(Panel(stream_table, title="[bold yellow]Stream Info[/bold yellow]", border_style="yellow"))
        main_grid.add_row(Panel(progress, title="[bold yellow]Performance[/bold yellow]", border_style="yellow"))
        main_grid.add_row(Text(f"Elapsed Time: {str(duration).split('.')[0]}", justify="center"))
        main_grid.add_row(footer)
        
        return Align.center(main_grid)

    with Live(generate_layout(), console=console, screen=True, auto_refresh=False, vertical_overflow="visible") as live:
        while not stop:
            if time.time() - last_check >= 2:
                get_viewer_count()
            live.update(generate_layout(), refresh=True)
            time.sleep(1)

# --- YOUR ORIGINAL ASYNC LOGIC (UNCHANGED) ---

async def token_fetcher():
    global stop, token_queue, target_token_pool
    while not stop:
        try:
            with token_lock:
                current_size = len(token_queue)
            if current_size < target_token_pool:
                loop = asyncio.get_running_loop()
                token = await loop.run_in_executor(executor, get_token)
                if token:
                    with token_lock:
                        token_queue.append(token)
            else:
                await asyncio.sleep(0.5)
        except:
            await asyncio.sleep(0.05)

async def get_token_from_pool():
    global token_queue
    while not stop:
        with token_lock:
            if token_queue:
                return token_queue.popleft()
        await asyncio.sleep(0.05)
    return None

async def websocket_handler(token):
    global connections, stop, channel_id, heartbeats, pings, attempts
    if not token: return
    attempts += 1
    connected = False
    try:
        url = f"wss://websockets.kick.com/viewer/v1/connect?token={token}"
        async with websockets.connect(url, open_timeout=5) as ws:
            connections += 1
            connected = True
            handshake = {"type": "channel_handshake", "data": {"message": {"channelId": channel_id}}}
            await ws.send(json.dumps(handshake))
            heartbeats += 1
            while not stop:
                await ws.send(json.dumps({"type": "ping"}))
                pings += 1
                await asyncio.sleep(12 + random.randint(1, 5))
    except:
        pass
    finally:
        if connected and connections > 0:
            connections -= 1

async def create_connection():
    while not stop:
        try:
            token = await get_token_from_pool()
            if token:
                await websocket_handler(token)
            await asyncio.sleep(random.uniform(0.1, 0.5))
        except:
            await asyncio.sleep(0.5)

async def connection_manager(num_connections):
    global stop, target_token_pool, connections_started
    target_token_pool = num_connections * 3
    num_fetchers = min(500, max(100, num_connections // 100))
    
    fetcher_tasks = [asyncio.create_task(token_fetcher()) for _ in range(num_fetchers)]
    
    min_tokens = min(500, num_connections)
    while len(token_queue) < min_tokens and not stop:
        await asyncio.sleep(1)
    
    connections_started = True
    
    tasks = [asyncio.create_task(create_connection()) for _ in range(num_connections)]
    
    await asyncio.gather(*tasks, *fetcher_tasks, return_exceptions=False)

def run(num_connections, channel_name):
    global max_connections, channel, start_time, channel_id, stop
    max_connections = int(num_connections)
    channel = clean_channel_name(channel_name)
    start_time = datetime.datetime.now()
    
    console.print(f"[green]✓ Project:[/] Kickerz")
    console.print(f"[green]✓ Channel:[/] {channel}")
    console.print(f"[green]✓ Connections:[/] {num_connections}")
    
    with console.status("[bold green]Initializing...[/bold green]"):
        if not get_channel_info(channel) or not stream_id:
            console.print("\n[bold red][FATAL][/bold red] Could not get channel info or stream ID. Channel is likely OFFLINE.")
            return

    stats_thread = Thread(target=rich_dashboard_thread, daemon=True)
    stats_thread.start()
    
    try:
        asyncio.run(connection_manager(max_connections))
    except KeyboardInterrupt:
        pass
    finally:
        stop = True

if __name__ == "__main__":
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
        channel_input = input("Enter channel name or URL: ").strip()
        thread_input = int(input("Enter number of viewers: ").strip())
        run(thread_input, channel_input)
    except (ValueError, KeyboardInterrupt):
        pass
    finally:
        stop = True
        console.print("\n[yellow]Script terminated.[/yellow]")
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

# Massive thread pool for parallel token fetching
executor = ThreadPoolExecutor(max_workers=500)

def clean_channel_name(name):
    if "kick.com/" in name:
        parts = name.split("kick.com/")
        channel = parts[1].split("/")[0].split("?")[0]
        return channel.lower()
    return name.lower()

def get_channel_info(name):
    global channel_id, stream_id
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        s.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://kick.com/',
            'Origin': 'https://kick.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
        
        try:
            response = s.get(f'https://kick.com/api/v2/channels/{name}')
            if response.status_code == 200:
                data = response.json()
                channel_id = data.get("id")
                if 'livestream' in data and data['livestream']:
                    stream_id = data['livestream'].get('id')
                return channel_id
        except:
            pass
        
        try:
            response = s.get(f'https://kick.com/api/v1/channels/{name}')
            if response.status_code == 200:
                data = response.json()
                channel_id = data.get("id")
                if 'livestream' in data and data['livestream']:
                    stream_id = data['livestream'].get('id')
                return channel_id
        except:
            pass
        
        print(f"Failed to get info for: {name}")
        return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    finally:
        if channel_id:
            print(f"Channel ID: {channel_id}")
        if stream_id:
            print(f"Stream ID: {stream_id}")

def get_token():
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        s.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
        
        try:
            s.get("https://kick.com")
            s.headers["X-CLIENT-TOKEN"] = CLIENT_TOKEN
            response = s.get('https://websockets.kick.com/viewer/v1/token')
            if response.status_code == 200:
                data = response.json()
                token = data.get("data", {}).get("token")
                if token:
                    return token
        except:
            pass
        
        return None
    except:
        return None

def get_viewer_count():
    global viewers, last_check
    if not stream_id:
        return 0
    
    try:
        s = tls_client.Session(client_identifier="chrome_120", random_tls_extension_order=True)
        s.headers.update({
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://kick.com/',
            'Origin': 'https://kick.com',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
        })
        
        url = f"https://kick.com/current-viewers?ids[]={stream_id}"
        response = s.get(url)
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                viewers = data[0].get('viewers', 0)
                last_check = time.time()
                return viewers
        return 0
    except:
        return 0

def show_stats():
    global stop, start_time, connections, attempts, pings, heartbeats, viewers, last_check, token_queue, target_token_pool, connections_started
    print("\n\n\n\n\n")
    os.system('cls' if os.name == 'nt' else 'clear')
    
    while not stop:
        try:
            now = time.time()
            
            # Update viewer count EVERY SECOND
            if now - last_check >= 1:
                get_viewer_count()
            
            if start_time:
                elapsed = datetime.datetime.now() - start_time
                duration = f"{int(elapsed.total_seconds())}s"
            else:
                duration = "0s"
            
            with token_lock:
                token_count = len(token_queue)
            
            ws_count = connections
            ws_attempts = attempts
            ping_count = pings
            heartbeat_count = heartbeats
            stream_display = stream_id if stream_id else 'N/A'
            viewer_display = viewers if viewers else 'N/A'
            
            pool_percentage = (token_count / target_token_pool * 100) if target_token_pool > 0 else 0
            status = "RUNNING" if connections_started else "BUILDING TOKENS"
            
            print("\033[5A", end="")
            print(f"\033[2K\r[x] Status: \033[33m{status}\033[0m | Connections: \033[32m{ws_count}\033[0m | Attempts: \033[32m{ws_attempts}\033[0m")
            print(f"\033[2K\r[x] Token Pool: \033[33m{token_count:,}/{target_token_pool:,}\033[0m (\033[36m{pool_percentage:.1f}%\033[0m)")
            print(f"\033[2K\r[x] Pings: \033[32m{ping_count}\033[0m | Heartbeats: \033[32m{heartbeat_count}\033[0m | Duration: \033[32m{duration}\033[0m")
            print(f"\033[2K\r[x] Stream ID: \033[32m{stream_display}\033[0m | Live Viewers: \033[36m{viewer_display}\033[0m")
            print(f"\033[2K\r[x] Updated: \033[32m{time.strftime('%H:%M:%S', time.localtime(last_check))}\033[0m")
            sys.stdout.flush()
            time.sleep(1)
        except:
            time.sleep(1)

async def token_fetcher():
    """Background task to keep token pool filled"""
    global stop, token_queue, target_token_pool
    
    while not stop:
        try:
            with token_lock:
                current_size = len(token_queue)
            
            if current_size < target_token_pool:
                loop = asyncio.get_event_loop()
                token = await loop.run_in_executor(executor, get_token)
                
                if token:
                    with token_lock:
                        token_queue.append(token)
            else:
                await asyncio.sleep(0.5)
        except Exception as e:
            await asyncio.sleep(0.05)

async def get_token_from_pool():
    """Get a token from the pool, wait if necessary"""
    global token_queue
    
    retries = 0
    while retries < 200:
        with token_lock:
            if token_queue:
                return token_queue.popleft()
        
        await asyncio.sleep(0.05)
        retries += 1
    
    return None

async def websocket_handler(token):
    global connections, stop, channel_id, heartbeats, pings, attempts
    
    if not token:
        return
    
    attempts += 1
    connected = False
    
    try:
        url = f"wss://websockets.kick.com/viewer/v1/connect?token={token}"
        
        async with websockets.connect(url) as ws:
            connections += 1
            connected = True
            
            handshake = {
                "type": "channel_handshake",
                "data": {"message": {"channelId": channel_id}}
            }
            await ws.send(json.dumps(handshake))
            heartbeats += 1
            
            # Keep pinging forever
            while not stop:
                ping = {"type": "ping"}
                await ws.send(json.dumps(ping))
                pings += 1
                
                sleep_time = 12 + random.randint(1, 5)
                await asyncio.sleep(sleep_time)
                
    except Exception as e:
        pass
    finally:
        if connected and connections > 0:
            connections -= 1

async def create_connection():
    """Get a token and create a websocket connection"""
    global stop
    
    while not stop:
        try:
            token = await get_token_from_pool()
            if token:
                await websocket_handler(token)
            await asyncio.sleep(random.uniform(0.1, 0.5))
        except:
            await asyncio.sleep(0.5)

async def connection_manager(num_connections):
    """Manage all websocket connections"""
    global stop, target_token_pool, connections_started
    
    # Calculate target token pool (3x the desired viewers)
    target_token_pool = num_connections * 3
    
    # Calculate number of token fetchers
    num_fetchers = min(500, max(100, num_connections // 100))
    
    print(f"\n{'='*60}")
    print(f"TARGET: {num_connections:,} live viewers")
    print(f"TOKEN POOL TARGET: {target_token_pool:,} tokens (3x viewers)")
    print(f"STARTING {num_fetchers} PARALLEL TOKEN FETCHERS")
    print(f"{'='*60}\n")
    
    # Start token fetchers in background
    fetcher_tasks = [asyncio.create_task(token_fetcher()) for _ in range(num_fetchers)]
    
    # Wait for minimum tokens (smaller requirement)
    min_tokens = min(500, num_connections)  # Start with just 500 tokens or num_connections, whichever is smaller
    print(f"Waiting for {min_tokens:,} tokens to start...")
    
    while len(token_queue) < min_tokens and not stop:
        await asyncio.sleep(1)
        print(f"Token pool: {len(token_queue):,}/{min_tokens:,}...")
    
    print(f"\n✓ Got {len(token_queue):,} tokens! Starting connections NOW!\n")
    connections_started = True
    
    # Create connection tasks immediately
    tasks = []
    for i in range(num_connections):
        task = asyncio.create_task(create_connection())
        tasks.append(task)
        
        if i % 100 == 0 and i > 0:
            print(f"Spawned {i:,}/{num_connections:,} connection tasks...")
            await asyncio.sleep(0.01)
    
    print(f"\n✓ All {num_connections:,} connection tasks started!\n")
    
    # Wait for all tasks
    try:
        await asyncio.gather(*tasks, *fetcher_tasks)
    except:
        pass

def run(num_connections, channel_name):
    global max_connections, channel, start_time, channel_id, stop
    
    max_connections = int(num_connections)
    channel = clean_channel_name(channel_name)
    start_time = datetime.datetime.now()
    channel_id = get_channel_info(channel)
    
    if not channel_id:
        print("Failed to get channel info")
        return
    
    # Start stats thread
    stats_thread = Thread(target=show_stats, daemon=True)
    stats_thread.start()
    
    # Run asyncio event loop
    try:
        asyncio.run(connection_manager(max_connections))
    except KeyboardInterrupt:
        stop = True
        print("\nStopping...")

if __name__ == "__main__":
    try:
        os.system('cls' if os.name == 'nt' else 'clear')
        channel_input = input("Enter channel name or URL: ").strip()
        if not channel_input:
            print("Channel name needed.")
            sys.exit(1)
        
        while True:
            try:
                thread_input = int(input("Enter number of viewers: ").strip())
                if thread_input > 0:
                    break
                else:
                    print("Must be greater than 0")
            except ValueError:
                print("Enter a valid number")
        
        run(thread_input, channel_input)
    except KeyboardInterrupt:
        stop = True
        print("\nStopping...")
        sys.exit(0)
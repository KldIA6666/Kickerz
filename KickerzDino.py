# ===================================================================================
# Project: KickerzDino (Kick Account Creator and Verifier)
# Developer: kia6666@rit.edu
#
# Disclaimer: This script is intended for educational and research purposes only.
# The developer is not responsible for any misuse of this software.
# By using this script, you agree to use it legally and ethically.
# ===================================================================================

import time
import names
import random
import secrets
import string
import re
import asyncio
from datetime import datetime
from botasaurus.browser import *
from mailtm import Email

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.prompt import Prompt

console = Console()

def generate_realistic_username():
    name1, name2 = names.get_first_name().lower(), names.get_first_name().lower()
    while name1 == name2: name2 = names.get_first_name().lower()
    return f"{name1}{name2}{random.randint(100, 9999)}"

def generate_complex_password(min_length=8, max_length=20):
    alphabet = string.ascii_letters + string.digits + string.punctuation
    while True:
        password = ''.join(secrets.choice(alphabet) for _ in range(random.randint(min_length, max_length)))
        if (any(c.islower() for c in password) and any(c.isupper() for c in password) and
            any(c.isdigit() for c in password) and any(c in string.punctuation for c in password)):
            return password

def human_type(driver: Driver, selector: str, text: str):
    for char in text:
        driver.type(selector, char)
        time.sleep(random.uniform(0.04, 0.11))

async def listener(message: dict, shared_data: dict, log_queue: asyncio.Queue):
    await log_queue.put("[[yellow]LISTENER[/yellow]] Checking new email...")
    subject = message.get('subject', '')
    match = re.search(r'^\s*(\d{6})', subject)
    if match:
        code = match.group(1)
        shared_data['verification_code'] = code
        await log_queue.put(f"[[yellow]LISTENER[/yellow]] Verification code found: [bold green]{code}[/bold green]")

@browser(output=None)
def register_on_kick_task(driver: Driver, data: dict):
    username = data['username']
    password = data['password']
    email = data['email']
    shared_data = data['shared_data']
    log_queue = data['log_queue']
    loop = data['loop']

    def log(message):
        asyncio.run_coroutine_threadsafe(log_queue.put(message), loop)

    log("[bold cyan]Applying stealth enhancements and navigating...[/bold cyan]")
    driver.enable_human_mode()
    try:
        driver.google_get("https://www.kick.com/", bypass_cloudflare=True)
        driver.run_js("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        if driver.is_element_present('[data-testid="accept-cookies"]', wait=5):
            driver.click('[data-testid="accept-cookies"]')
            log("Accepted cookies.")
        else:
            log("No cookie banner found, continuing.")
    except Exception as e:
        log(f"[bold red]CRITICAL ERROR during navigation:[/bold red] {e}")
        driver.save_screenshot("error_navigation.png")
        return

    try:
        log("Filling registration form...")
        driver.click_element_containing_text("Sign Up")
        driver.short_random_sleep()
        human_type(driver, "input[name='email']", email)
        driver.type("input[name='birthdate']", "10-10-2000")
        human_type(driver, "input[name='username']", username)
        human_type(driver, "input[name='password']", password)
        driver.click('[data-testid="sign-up-submit"]')
        log("Registration form submitted.")
    except Exception as e:
        log(f"[bold red]CRITICAL ERROR while filling the form:[/bold red] {e}")
        driver.save_screenshot("error_form_fill.png")
        return

    try:
        log("Waiting for the 6-digit security code prompt...")
        driver.get_element_containing_text("Please enter the 6-digit security code", wait=30)
        log("Waiting for verification email...")
        timeout = 60
        start_time = time.time()
        while shared_data['verification_code'] is None:
            if time.time() - start_time > timeout:
                raise Exception("Timed out waiting for verification code.")
            time.sleep(1)
        code = shared_data['verification_code']
        log(f"Entering received code: {code}")
        human_type(driver, "input[name='code']", code)
    except Exception as e:
        log(f"[bold red]CRITICAL ERROR during email verification:[/bold red] {e}")
        driver.save_screenshot("error_verification_step.png")
        return

    try:
        tos_box_selector = '[data-radix-scroll-area-viewport]'
        log("Handling Terms of Service...")
        if driver.is_element_present(tos_box_selector, wait=15):
            scrollable_element = driver.select(tos_box_selector)
            while scrollable_element.can_scroll_further():
                scrollable_element.scroll_to_bottom(smooth_scroll=True)
                time.sleep(0.5)
            driver.click("button[type='submit']")
            log("Agreed to Terms and Conditions.")
        else:
            log("Terms of Service box not found, assuming it's not required.")
    except Exception as e:
        log(f"[bold red]CRITICAL ERROR during Terms of Service step:[/bold red] {e}")
        driver.save_screenshot("error_tos_step.png")
        return

    log("Verifying account creation success...")
    driver.short_random_sleep()
    channel_link_selector = f"a[href='/{username}']"
    if driver.is_element_present(channel_link_selector, wait=Wait.LONG):
        success_message = f"[bold green]SUCCESS:[/] Account creation confirmed for [bold]{username}[/bold]."
        log(success_message)
        with open("successful_accounts.csv", 'a') as f:
            f.write(f"{username},{password},{email}\n")
        log(f"Credentials saved for user: [bold]{username}[/bold]")
    else:
        failure_message = "[bold red]FAILURE:[/] Channel link not found. Account creation likely failed."
        log(failure_message)
        driver.save_screenshot("error_final_verification_failed.png")

    log("[bold yellow]Automation complete. Press Enter in the console to close the browser.[/bold yellow]")

async def log_updater(queue: asyncio.Queue, log_panel: Panel, max_lines: int = 50):
    log_content = []
    while True:
        message = await queue.get()
        if message is None:
            break
        
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_content.append(Text.from_markup(f"[dim]{timestamp}[/dim] {message}"))

        # Trim the log to prevent it from growing indefinitely
        if len(log_content) > max_lines:
            log_content = log_content[-max_lines:]

        log_panel.renderable = Text("\n").join(log_content)
        queue.task_done()

async def main():
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(ratio=1, name="main"),
        Layout(size=3, name="footer"),
    )
    layout["header"].update(Panel("[bold blue]KickerzDino Account Creator[/bold blue]", style="blue"))
    layout["footer"].update(Panel(Text("Developer: kia6666@rit.edu | For Educational & Research Purposes Only.", justify="center"), style="bold blue"))
    
    log_panel = Panel(Text(""), title="[green]Live Log[/green]", border_style="green")
    layout["main"].update(log_panel)

    log_queue = asyncio.Queue()

    username = generate_realistic_username()
    password = generate_complex_password()
    email_client = Email()
    await asyncio.to_thread(email_client.register, username=username)
    email = email_client.address

    credentials_text = (
        f"[yellow]---- Generated Credentials ----[/yellow]\n"
        f"[bold]Username:[/] {username}\n"
        f"[bold]Password:[/] {password}\n"
        f"[bold]Email:[/b]    {email}"
    )
    await log_queue.put(credentials_text)

    shared_data = {'verification_code': None}
    
    with Live(layout, screen=True, redirect_stderr=False, refresh_per_second=10) as live:
        updater_task = asyncio.create_task(log_updater(log_queue, log_panel))
        
        loop = asyncio.get_running_loop()
        listener_callback = lambda msg: asyncio.run_coroutine_threadsafe(listener(msg, shared_data, log_queue), loop)
        
        listener_task = asyncio.create_task(
            asyncio.to_thread(email_client.start, listener_callback)
        )
        await log_queue.put("Email listener started in the background.")

        task_data = {
            'username': username, 'password': password, 'email': email,
            'shared_data': shared_data, 'log_queue': log_queue, 'loop': loop
        }

        await asyncio.to_thread(register_on_kick_task, data=task_data)

        listener_task.cancel()
        try:
            await listener_task
        except asyncio.CancelledError:
            await log_queue.put("Listener stopped successfully.")

        await log_queue.put(None)
        await updater_task

    Prompt.ask("[bold yellow]Press Enter to exit.[/bold yellow]")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        console.print("\n[bold red]Script interrupted by user. Exiting.[/bold red]")
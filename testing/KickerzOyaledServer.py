# ===================================================================================
# Project: KickerzOyaled (Interactive Kick Bot)
# Developer: kia6666@rit.edu & Gemini AI (Gave it Libraries Entire Code & Got Recomendations as Opposed to Reading Documentation's & Tips)
#
# A MESSAGE TO THE STAR-BEGGARS:
# This project (and previous tools) were created out of frustration with projects like AdamBankz's kick-viewbot (https://github.com/AdamBankz/kick-viewbot),
# which lock basic features behind arbitrary "Star Goals" and paywalls.
# Open source should be about collaboration and freedom, not begging for GitHub stars (goofball)
# while hiding "updated versions" that are never released.
#
# This code is free. It's powerful. No star goals. No premium Discord. Just build.
#
# Disclaimer: This script is intended for educational and research purposes only.
# The developer is not responsible for any misuse of this software.
# By using this script, you agree to use it legally and ethically.
# ===================================================================================

import time
import re
import asyncio
import random
import os
import threading
import platform
from datetime import datetime
from botasaurus.browser import *
from mailtm import Email
from google import genai
from google.genai import types
from colorama import init, Fore, Style

# --- Global Variables & Configuration ---
GEMINI_API_KEY = None
init(autoreset=True)
LAST_ACTION_STATUS = "Bot initialized. Waiting for first command."

# --- A reliable stop event for long-running tasks ---
stop_event = threading.Event()

# --- Helper Functions ---

class Colors:
    INFO = Fore.BLUE
    SUCCESS = Fore.GREEN
    WARNING = Fore.YELLOW
    ERROR = Fore.RED
    RESET = Style.RESET_ALL

def clear_screen():
    os.system('cls' if platform.system() == 'Windows' else 'clear')

def print_log(message, level="INFO", is_status=False, mode_name=None):
    global LAST_ACTION_STATUS
    timestamp = datetime.now().strftime("%H:%M:%S")
    color = getattr(Colors, level, Colors.INFO)
    
    prefix = f"[{timestamp}] "
    if mode_name:
        prefix += f"({mode_name}) "
        
    log_message = f"{prefix}{message}"
    print(f"{color}{log_message}")

    if is_status:
        LAST_ACTION_STATUS = f"{color}{log_message}"

def print_menu():
    clear_screen()
    print(f"{Colors.SUCCESS}Last Action: {LAST_ACTION_STATUS}\n")
    print("\n" + "="*30 + " KickerzOyaled Control Menu " + "="*30)
    print("  [1] Manual Chat            - Send a single message.")
    print("  [2] File-Based Chatter     - Send messages from messages.txt.")
    print("  [3] Question Asker         - Ask a question from questions.txt.")
    print("  [4] Emoji Spammer          - Spam random quick emotes.")
    print("  [5] Hype Train Mode        - Spam a manual or AI-generated hype message.")
    print("\n  --- AI Mode ---")
    print("  [A] AI Vision Analyst      - Generate and send comment(s) based on a stream screenshot.")
    print("\n  --- Automated & Channel Actions ---")
    print("  [M] Automated Mode         - Run a random selection of modes continuously.")
    print("  [F] Toggle Follow          - Follow or Unfollow the channel.")
    print("  [C] Run Command            - Send a chat command (e.g., !uptime).")
    print("  [Q] Quit                   - Exit the bot.")
    print(f"{Colors.INFO}{'='*84}")
    print(f"{Colors.SUCCESS}Developer: kia6666@rit.edu | For Educational & Research Purposes Only.")
    print(f"{Colors.INFO}{'='*84}")

def human_type(driver: Driver, selector: str, text: str):
    # Clear the field before typing to prevent appending text
    driver.clear(selector)
    for char in text:
        driver.type(selector, char)
        # Faster typing speed
        time.sleep(random.uniform(0.03, 0.06))

async def listener(message: dict, shared_data: dict):
    print_log("LISTENER: Checking new email...")
    subject = message.get('subject', '')
    match = re.search(r'^\s*(\d{6})', subject)
    if match:
        code = match.group(1)
        shared_data['verification_code'] = code
        print_log(f"LISTENER: Verification code found: {code}", "SUCCESS")

def wait_for_enter_to_stop():
    input()
    stop_event.set()

def get_gemini_api_key(mode_name="System"):
    global GEMINI_API_KEY
    if GEMINI_API_KEY: return GEMINI_API_KEY
    key = input(f"{Colors.WARNING}Please enter your Google Gemini API Key: ").strip()
    if not key:
        print_log("API Key cannot be empty.", "ERROR", is_status=True, mode_name=mode_name)
        return None
    GEMINI_API_KEY = key
    os.environ['GOOGLE_API_KEY'] = key
    return key

def load_from_file(filename, mode_name="File-Loader"):
    if not os.path.exists(filename):
        print_log(f"'{filename}' not found. Please create it.", "ERROR", is_status=True, mode_name=mode_name)
        return []
    with open(filename, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
    if not lines:
        print_log(f"'{filename}' is empty.", "WARNING", is_status=True, mode_name=mode_name)
    return lines

def run_interruptible_mode(target_func, mode_name, *args):
    stop_event.clear()
    mode_thread = threading.Thread(target=target_func, args=args, daemon=True)
    mode_thread.start()
    print_log("Running... Press [Enter] to stop and return to menu.", "WARNING", mode_name=mode_name)
    
    input_thread = threading.Thread(target=wait_for_enter_to_stop, daemon=True)
    input_thread.start()
    
    mode_thread.join()
    
    if stop_event.is_set():
        print_log("Action stopped by user.", "WARNING", is_status=True, mode_name=mode_name)

# --- All Mode Functions Now Live Outside The Main Task ---
def send_chat_message(driver: Driver, message: str, fast_mode=False, mode_name="Chat"):
    CHAT_INPUT_SELECTOR = '[data-testid="chat-input"]'
    DESKTOP_SEND_BUTTON_SELECTOR = '#chatroom-send-button'
    MOBILE_SEND_BUTTON_SELECTOR = 'div.ml-auto button:not(.hidden)'

    try:
        chat_input = driver.wait_for_element(CHAT_INPUT_SELECTOR, wait=10)
        if not chat_input:
            print_log("Chat input field could not be found.", "ERROR", mode_name=mode_name)
            return False

        print_log(f"Typing: '{message}'", mode_name=mode_name)

        if fast_mode:
            chat_input.click()
            chat_input.clear()
            driver.type(CHAT_INPUT_SELECTOR, message)
        else:
            human_type(driver, CHAT_INPUT_SELECTOR, message)
        
        time.sleep(0.2)

        if driver.is_element_present(DESKTOP_SEND_BUTTON_SELECTOR, wait=1):
            driver.click(DESKTOP_SEND_BUTTON_SELECTOR)
            return True
        
        mobile_send_button = driver.select(MOBILE_SEND_BUTTON_SELECTOR, wait=2)
        if mobile_send_button:
            mobile_send_button.click()
            return True

        print_log("Could not find a valid VISIBLE send button after typing.", "ERROR", mode_name=mode_name)
        driver.save_screenshot("error_send_button_not_found.png")
        return False

    except Exception as e:
        print_log(f"An unexpected error occurred in send_chat_message: {e}", "ERROR", mode_name=mode_name)
        driver.save_screenshot(f"error_send_message_unexpected_{datetime.now().strftime('%H%M%S')}.png")
        return False

def toggle_follow(driver: Driver):
    mode_name = "Follow"
    MAIN_FOLLOW_BUTTON_SELECTOR = '[data-testid="follow-button"]'
    DIALOG_SELECTOR = 'div[role="dialog"]'
    DIALOG_FOLLOW_BUTTON_SELECTOR = f'{DIALOG_SELECTOR} button[aria-label="Follow"]'
    DIALOG_UNFOLLOW_BUTTON_SELECTOR = f'{DIALOG_SELECTOR} button[aria-label="Unfollow"]'
    UNFOLLOW_CONFIRM_BUTTON_SELECTOR = "button.bg-red-500" # Desktop only

    try:
        main_follow_button = driver.wait_for_element(MAIN_FOLLOW_BUTTON_SELECTOR, wait=10)
        if not main_follow_button:
            print_log("Could not find the main follow button.", "ERROR", is_status=True, mode_name=mode_name)
            return

        initial_label = main_follow_button.get_attribute('aria-label')
        main_follow_button.click()
        time.sleep(1)

        if driver.is_element_present(DIALOG_SELECTOR, wait=2):
            print_log("Mobile dialog detected.", mode_name=mode_name)
            if "Unfollow" in initial_label:
                dialog_unfollow_btn = driver.wait_for_element(DIALOG_UNFOLLOW_BUTTON_SELECTOR, wait=5)
                if dialog_unfollow_btn:
                    dialog_unfollow_btn.click()
                    print_log("Clicked Unfollow inside mobile dialog.", mode_name=mode_name)
                else:
                    print_log("Could not find Unfollow button in mobile dialog.", "ERROR", is_status=True, mode_name=mode_name)
            elif "Follow" in initial_label:
                dialog_follow_btn = driver.wait_for_element(DIALOG_FOLLOW_BUTTON_SELECTOR, wait=5)
                if dialog_follow_btn:
                    dialog_follow_btn.click()
                    print_log("Clicked Follow inside mobile dialog.", mode_name=mode_name)
                else:
                    print_log("Could not find Follow button in mobile dialog.", "ERROR", is_status=True, mode_name=mode_name)
        
        elif "Unfollow" in initial_label:
            print_log("Desktop view detected. Confirming unfollow...", mode_name=mode_name)
            driver.click(UNFOLLOW_CONFIRM_BUTTON_SELECTOR, wait=5)
        
        time.sleep(2)
        final_label = driver.get_attribute(MAIN_FOLLOW_BUTTON_SELECTOR, 'aria-label', wait=5)
        
        if "Unfollow" in initial_label and "Follow" in final_label:
            print_log("Successfully unfollowed the channel.", "SUCCESS", is_status=True, mode_name=mode_name)
        elif "Follow" in initial_label and "Unfollow" in final_label:
            print_log("Successfully followed the channel.", "SUCCESS", is_status=True, mode_name=mode_name)
        else:
            print_log(f"Action may have failed. Initial: '{initial_label}', Final: '{final_label}'", "ERROR", is_status=True, mode_name=mode_name)

    except Exception as e:
        print_log(f"Error toggling follow: {e}", "ERROR", is_status=True, mode_name=mode_name)

def run_manual_chat(driver: Driver):
    mode_name = "Manual Chat"
    msg = input(f"{Colors.WARNING}Enter message to send: ")
    if msg:
        if send_chat_message(driver, msg, mode_name=mode_name):
            print_log("Message sent.", "SUCCESS", is_status=True, mode_name=mode_name)
        else:
            print_log("Failed to send message.", "ERROR", is_status=True, mode_name=mode_name)

def _file_chatter_loop(driver: Driver, choice: str):
    mode_name = "File Chatter"
    messages = load_from_file('messages.txt', mode_name=mode_name)
    if not messages: return

    print_log(f"Starting to send messages {'sequentially' if choice == 'S' else 'randomly'}...", mode_name=mode_name)
    
    message_list = list(messages)
    
    while not stop_event.is_set():
        if not message_list and choice == 'S':
            print_log("Finished all messages in sequence.", "SUCCESS", is_status=True, mode_name=mode_name)
            break
            
        current_message = message_list.pop(0) if choice == 'S' else random.choice(messages)
        
        send_chat_message(driver, current_message, mode_name=mode_name)
        
        delay = random.uniform(5, 30)
        print_log(f"Waiting for {delay:.1f} seconds...", mode_name=mode_name)
        for _ in range(int(delay * 2)):
            if stop_event.is_set(): break
            time.sleep(0.5)

def run_file_chatter(driver: Driver):
    choice = input(f"{Colors.WARNING}Send (S)equentially or (R)andomly? ").upper()
    if choice not in ['S', 'R']:
        print_log("Invalid choice.", "ERROR", is_status=True, mode_name="File Chatter")
        return
    run_interruptible_mode(_file_chatter_loop, "File Chatter", driver, choice)

def run_question_asker(driver: Driver):
    mode_name = "Question Asker"
    questions = load_from_file('questions.txt', mode_name=mode_name)
    if questions:
        print_log("Choosing a random question...", mode_name=mode_name)
        if send_chat_message(driver, random.choice(questions), mode_name=mode_name):
            print_log("Question sent.", "SUCCESS", is_status=True, mode_name=mode_name)

def _emoji_spammer_loop(driver: Driver):
    mode_name = "Emoji Spammer"
    
    DESKTOP_EMOTES_SELECTOR = '#quick-emotes-holder img'
    MOBILE_EMOTE_TOGGLE_BUTTON_SELECTOR = '#chat-input-wrapper button'
    MOBILE_EMOTE_PICKER_IMAGES_SELECTOR = 'div[class*="grid-cols-8"] button img'

    emote_alts = []
    
    if driver.is_element_present(DESKTOP_EMOTES_SELECTOR, wait=3):
        print_log("Desktop view detected for emotes.", mode_name=mode_name)
        emotes = driver.select_all(DESKTOP_EMOTES_SELECTOR, wait=2)
        if emotes:
            emote_alts = [emote.get_attribute('alt') for emote in emotes]
    else:
        print_log("Mobile view detected. Using emote picker dialog.", mode_name=mode_name)
        try:
            emote_toggle_button = driver.select(MOBILE_EMOTE_TOGGLE_BUTTON_SELECTOR, wait=5)
            if not emote_toggle_button:
                raise Exception("Could not find the mobile emote toggle button.")
            
            print_log("Opening emote picker...", mode_name=mode_name)
            emote_toggle_button.click()
            time.sleep(1)

            emotes_in_picker = driver.select_all(MOBILE_EMOTE_PICKER_IMAGES_SELECTOR, wait=5)
            if emotes_in_picker:
                emote_alts = [alt for emote in emotes_in_picker if (alt := emote.get_attribute('alt'))]

            print_log("Closing emote picker...", mode_name=mode_name)
            emote_toggle_button.click()
            time.sleep(0.5)

        except Exception as e:
            print_log(f"Error during mobile emote discovery: {e}", "ERROR", mode_name=mode_name)
            driver.save_screenshot("error_emoji_mobile.png")
            return

    if not emote_alts:
        print_log("Could not find any emotes to spam.", "ERROR", is_status=True, mode_name=mode_name)
        return

    print_log(f"Found {len(emote_alts)} emotes. Starting spam...", mode_name=mode_name)
    while not stop_event.is_set():
        emote_to_send = f":{random.choice(emote_alts)}:"
        send_chat_message(driver, emote_to_send, fast_mode=True, mode_name=mode_name)
        time.sleep(random.uniform(1.0, 3.5))

def run_emoji_spammer(driver: Driver):
    run_interruptible_mode(_emoji_spammer_loop, "Emoji Spammer", driver)

def _hype_train_loop(driver: Driver, hype_msg: str):
    mode_name = "Hype Train"
    print_log(f"Starting Hype Train with message: '{hype_msg}'...", mode_name=mode_name)
    while not stop_event.is_set():
        send_chat_message(driver, hype_msg, fast_mode=True, mode_name=mode_name)
        time.sleep(random.uniform(0.5, 1.2))

def run_hype_train(driver: Driver):
    mode_name = "Hype Train"
    choice = input(f"{Colors.WARNING}(M)anual Hype or (A)I Generated Hype? ").upper()
    hype_msg = None
    if choice == 'M':
        hype_msg = input(f"{Colors.WARNING}Enter hype message (e.g., POG): ")
    elif choice == 'A':
        api_key = get_gemini_api_key(mode_name)
        if not api_key: return
        
        print_log("Taking a quick screenshot for AI Hype message...", mode_name=mode_name)
        output_dir = "output"; os.makedirs(output_dir, exist_ok=True)
        screenshot_path = os.path.join(output_dir, "stream_capture.png")
        driver.save_screenshot(screenshot_path)

        with open(screenshot_path, 'rb') as f: image_bytes = f.read()
        
        print_log("Sending to Gemini for a hype message...", mode_name=mode_name)
        client = genai.Client()
        prompt = "Based on this screenshot, generate one short, energetic, all-caps hype message. Just the message, nothing else."
        
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=[types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'), prompt]
        )
        hype_msg = response.text.strip().replace('"', '')
        print_log(f"AI generated hype: '{hype_msg}'", "SUCCESS", mode_name=mode_name)
    
    if hype_msg:
        run_interruptible_mode(_hype_train_loop, mode_name, driver, hype_msg)
    else:
        print_log("No hype message provided.", "ERROR", is_status=True, mode_name=mode_name)

def run_gemini_vision(driver: Driver, is_automated=False, auto_comment_count=3):
    mode_name = "AI Vision"
    api_key = get_gemini_api_key(mode_name)
    if not api_key: return

    count = auto_comment_count if is_automated else 1
    if not is_automated:
        list_choice = input(f"{Colors.WARNING}Generate a (S)ingle comment or a (L)ist of options? ").upper()
        if list_choice == 'L':
            try:
                count = int(input(f"{Colors.WARNING}How many comments to generate? (e.g., 3): "))
                if count < 1: count = 1
            except ValueError:
                print_log("Invalid number, defaulting to 3.", "WARNING", mode_name=mode_name)
                count = 10
    
    output_dir = "output"; os.makedirs(output_dir, exist_ok=True)
    screenshot_path = os.path.join(output_dir, "stream_capture.png")
    print_log("Taking screenshot for analysis...", mode_name=mode_name)
    driver.save_screenshot(screenshot_path)
    with open(screenshot_path, 'rb') as f: image_bytes = f.read()
    
    print_log("Sending to Gemini Vision API...", mode_name=mode_name)
    client = genai.Client()
    prompt_verb = "You are an automated chatter on Kick." if is_automated else "You are a chatter on Kick."
    prompt = f"{prompt_verb} Based on this screenshot, generate {count} unique, short, engaging, and relevant text comments. Keep them casual. Each on a new line, no numbering."
    
    response = client.models.generate_content(
        model='gemini-flash-latest',
        contents=[types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'), prompt]
    )
    suggestions = [line.strip().replace('"', '') for line in response.text.split('\n') if line.strip()]
    
    if not suggestions:
        print_log("AI could not generate suggestions.", "ERROR", is_status=True, mode_name=mode_name)
        return
    
    if is_automated:
        print_log(f"Automator: AI generated {len(suggestions)} comments. Sending all...", mode_name=mode_name)
        for sug in suggestions:
            if stop_event.is_set(): break
            send_chat_message(driver, sug, mode_name=mode_name)
            time.sleep(random.uniform(2, 5))
        print_log("Automator finished sending AI suggestions.", "SUCCESS", is_status=True, mode_name="Automated Mode")
        return

    print_log("AI Suggestions:", "SUCCESS", mode_name=mode_name)
    for i, sug in enumerate(suggestions):
        print(f"  [{i+1}] {sug}")
    
    action = input(f"{Colors.WARNING}Enter number to send, 'A' to send all, or '0' to cancel: ").upper()
    
    if action == 'A':
        print_log(f"Sending all {len(suggestions)} suggestions...", mode_name=mode_name)
        for sug in suggestions:
            send_chat_message(driver, sug, mode_name=mode_name)
            time.sleep(random.uniform(2, 5))
        print_log("Finished sending all AI suggestions.", "SUCCESS", is_status=True, mode_name=mode_name)
    else:
        try:
            selection_idx = int(action) - 1
            if 0 <= selection_idx < len(suggestions):
                send_chat_message(driver, suggestions[selection_idx], mode_name=mode_name)
                print_log("AI suggestion sent.", "SUCCESS", is_status=True, mode_name=mode_name)
            else:
                print_log("Selection cancelled.", "INFO", is_status=True, mode_name=mode_name)
        except (ValueError, IndexError):
            print_log("Invalid selection.", "ERROR", is_status=True, mode_name=mode_name)

def run_command(driver: Driver):
    mode_name = "Command"
    command = input(f"{Colors.WARNING}Enter command (e.g., !uptime): ")
    if command:
        if send_chat_message(driver, command, mode_name=mode_name):
            print_log(f"Command '{command}' sent.", "SUCCESS", is_status=True, mode_name=mode_name)

def _automated_mode_loop(driver: Driver, valid_keys: list):
    mode_name = "Automated Mode"
    while not stop_event.is_set():
        selected_key = random.choice(valid_keys)
        print_log(f"Next action will be Mode '{selected_key}'", mode_name=mode_name)
        
        delay = random.uniform(5, 30)
        print_log(f"Waiting for {delay:.1f}s before starting...", mode_name=mode_name)
        for _ in range(int(delay)):
            if stop_event.is_set(): break
            time.sleep(1)
        if stop_event.is_set(): break

        if selected_key == 'A':
            run_gemini_vision(driver, is_automated=True)
        elif selected_key == '5':
            print_log("Running AI Hype Train for a short burst...", mode_name=mode_name)
            # This is a non-interruptible burst for simplicity in auto mode
            output_dir = "output"; os.makedirs(output_dir, exist_ok=True)
            screenshot_path = os.path.join(output_dir, "stream_capture.png")
            driver.save_screenshot(screenshot_path)
            with open(screenshot_path, 'rb') as f: image_bytes = f.read()
            
            client = genai.Client()
            prompt = "Based on this screenshot, generate one short, energetic, all-caps hype message. Just the message, nothing else."
            response = client.models.generate_content(
                model='gemini-flash-latest',
                contents=[types.Part.from_bytes(data=image_bytes, mime_type='image/jpeg'), prompt]
            )
            hype_msg = response.text.strip().replace('"', '')
            if hype_msg:
                start_time = time.time()
                while time.time() - start_time < random.uniform(10, 20):
                    if stop_event.is_set(): break
                    send_chat_message(driver, hype_msg, fast_mode=True, mode_name=mode_name)
                    time.sleep(random.uniform(0.5, 1.2))
        
        # --- THIS IS THE CORRECTED LOGIC ---
        elif selected_key == '4':
            duration = random.uniform(15, 30)
            print_log(f"Running emoji spam for {duration:.1f} seconds...", mode_name=mode_name)
            
            # Get the list of emotes once before the loop
            DESKTOP_EMOTES_SELECTOR = '#quick-emotes-holder img'
            MOBILE_EMOTE_TOGGLE_BUTTON_SELECTOR = '#chat-input-wrapper button'
            MOBILE_EMOTE_PICKER_IMAGES_SELECTOR = 'div[class*="grid-cols-8"] button img'
            emote_alts = []
            
            if driver.is_element_present(DESKTOP_EMOTES_SELECTOR, wait=2):
                emotes = driver.select_all(DESKTOP_EMOTES_SELECTOR)
                if emotes: emote_alts = [e.get_attribute('alt') for e in emotes]
            else:
                try:
                    emote_toggle_button = driver.select(MOBILE_EMOTE_TOGGLE_BUTTON_SELECTOR)
                    if emote_toggle_button:
                        emote_toggle_button.click()
                        time.sleep(1)
                        emotes_in_picker = driver.select_all(MOBILE_EMOTE_PICKER_IMAGES_SELECTOR, wait=3)
                        if emotes_in_picker:
                            emote_alts = [alt for alt in [e.get_attribute('alt') for e in emotes_in_picker] if alt]
                        emote_toggle_button.click() # Close it back
                        time.sleep(0.5)
                except Exception as e:
                    print_log(f"Automated emoji spam failed to get mobile emotes: {e}", "ERROR", mode_name=mode_name)

            if not emote_alts:
                print_log("Automated emoji spam could not find any emotes.", "WARNING", mode_name=mode_name)
            else:
                start_time = time.time()
                while time.time() - start_time < duration:
                    if stop_event.is_set(): break
                    emote_to_send = f":{random.choice(emote_alts)}:"
                    send_chat_message(driver, emote_to_send, fast_mode=True, mode_name=mode_name)
                    time.sleep(random.uniform(1.0, 3.0))
        # --- END OF CORRECTION ---

        elif selected_key == '2':
            print_log("Sending a random message from file...", mode_name=mode_name)
            messages = load_from_file('messages.txt', mode_name=mode_name)
            if messages: send_chat_message(driver, random.choice(messages), mode_name=mode_name)
        elif selected_key == '3':
            print_log("Sending a random question from file...", mode_name=mode_name)
            questions = load_from_file('questions.txt', mode_name=mode_name)
            if questions: send_chat_message(driver, random.choice(questions), mode_name=mode_name)

def run_automated_mode(driver: Driver):
    mode_name = "Automated Mode"
    playlist_str = input(f"{Colors.WARNING}Enter modes for playlist (e.g., 2,3,4,5,A): ")
    playlist_keys = [key.strip().upper() for key in playlist_str.split(',')]
    
    AUTOMATION_SAFE_MODES = ['2', '3', '4', '5', 'A'] 
    valid_keys = [key for key in playlist_keys if key in AUTOMATION_SAFE_MODES]
    
    if not valid_keys:
        print_log("No valid, automatable modes selected. (Valid: 2, 3, 4, 5, A)", "ERROR", is_status=True, mode_name=mode_name)
        return

    if 'A' in valid_keys or '5' in valid_keys:
        if not get_gemini_api_key(mode_name):
            print_log("Gemini API key not provided. AI modes will be skipped.", "WARNING", is_status=True, mode_name=mode_name)
            valid_keys = [k for k in valid_keys if k not in ['A', '5']]
    
    if not valid_keys:
        print_log("No runnable modes left in playlist after API key check.", "ERROR", is_status=True, mode_name=mode_name)
        return
    
    print_log(f"Starting Automated Mode with playlist: {valid_keys}")
    run_interruptible_mode(_automated_mode_loop, mode_name, driver, valid_keys)

# --- Main Bot Task ---
@browser(output=None, headless=False, add_arguments=["--no-sandbox","--disable-gpu","--disable-dev-shm-usage"])
def interactive_chatter_task(driver: Driver, data: dict):
    # --- Step 1 & 2: Login and Navigation ---
    try:
        username = data['username']
        password = data['password']
        shared_data = data['shared_data']
        manual_mode = data.get('manual_mode', False)
        channel_name = data['channel_name']
        
        print_log("Applying stealth enhancements and navigating to Kick.com...")
        driver.enable_human_mode()
        driver.google_get("https://www.kick.com/", bypass_cloudflare=True)
        driver.run_js("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        if driver.is_element_present('[data-testid="accept-cookies"]', wait=5):
            driver.click('[data-testid="accept-cookies"]')
            print_log("Accepted cookies.")
        
        print_log("Navigating to the login form...")
        try:
            driver.click_element_containing_text("Log In", wait=5)
        except Exception:
            print_log("Login button not visible. Trying mobile fallback...", "WARNING")
            profile_icon_selector = "button[data-testid='login']"
            profile_icon = driver.select(profile_icon_selector, wait=5)
            
            if profile_icon:
                profile_icon.click()
                time.sleep(1)
                driver.click_element_containing_text("Log In", wait=5)
            else:
                raise Exception("Could not find the 'Log In' button or the mobile profile icon.")

        if not driver.is_element_present('form button[data-testid="login-submit"]', wait=5):
             raise Exception("Login modal did not appear after clicking login button.")
        
        print_log("Login modal opened. Filling form...")
        human_type(driver, "input[name='emailOrUsername']", username)
        human_type(driver, "input[name='password']", password)
        
        print_log("Submitting login form...")
        driver.click('button[data-testid="login-submit"]')
        
        if not driver.get_element_containing_text("Please enter the 6-digit security code", wait=30):
            raise Exception("Security code prompt did not appear.")
        
        code = None
        if manual_mode:
            print("\n" + "="*50)
            print_log("ACTION REQUIRED: CHECK YOUR EMAIL", "WARNING")
            while True:
                code = input(f"{Colors.WARNING}Please enter the 6-digit security code here: ").strip()
                if code.isdigit() and len(code) == 6: break
                else: print_log("Invalid input. Please enter exactly 6 numbers.", "ERROR")
            print("="*50 + "\n")
        else:
            timeout = 60; start_time = time.time()
            print_log("Waiting for verification code from email listener...")
            while shared_data.get('verification_code') is None:
                if time.time() - start_time > timeout:
                    raise Exception("Timed out waiting for verification code via automation.")
                time.sleep(1)
            code = shared_data['verification_code']

        print_log(f"Entering OTP code: {code}")
        human_type(driver, "input[name='code']", code)
        time.sleep(2)

        if driver.get_element_containing_text(text="The provided 2FA code is wrong", wait=3):
            raise Exception("Kick reported 'The provided 2FA code is wrong'. Halting.")

        print_log("Verifying successful login...")
        login_verified = False
        start_time = time.time()
        timeout = 30
        
        desktop_selector = "nav a[href*='/dashboard/']"
        mobile_selector = 'button[data-testid="navbar-account"] img'

        while time.time() - start_time < timeout:
            if driver.is_element_present(desktop_selector, wait=1):
                login_verified = True
                print_log("Desktop login element found.", "SUCCESS")
                break
            
            profile_img = driver.select(mobile_selector, wait=1)
            if profile_img:
                alt_text = profile_img.get_attribute("alt")
                if alt_text and alt_text.lower() == username.lower():
                    login_verified = True
                    print_log(f"Mobile login element found for user '{alt_text}'.", "SUCCESS")
                    break
            
            time.sleep(1)

        if not login_verified:
            raise Exception(f"Login verification failed. Could not find a valid desktop or mobile profile element within {timeout} seconds.")
        
        print_log(f"SUCCESS: Login confirmed for user '{username}'.", "SUCCESS", is_status=True)

        channel_url = f"https://kick.com/{channel_name}"
        print_log(f"Navigating to channel: {channel_name}")
        driver.get(channel_url)
        driver.wait_for_element('[data-testid="chat-input"]', wait=20)
        print_log("Successfully entered the channel chat.", "SUCCESS", is_status=True)
    
    except Exception as e:
        print_log(f"CRITICAL ERROR during setup: {e}", "ERROR", is_status=True)
        driver.save_screenshot("error_setup_phase.png")
        return

    # --- Step 3: Main Control Loop ---
    modes = {
        '1': run_manual_chat, '2': run_file_chatter, '3': run_question_asker,
        '4': run_emoji_spammer, '5': run_hype_train, 'A': run_gemini_vision,
        'M': run_automated_mode, 'F': toggle_follow, 'C': run_command
    }

    while True:
        try:
            print_menu()
            choice = input(f"{Colors.WARNING}Enter your choice: ").upper()

            if choice == 'Q':
                print_log("Quitting...")
                break
            
            if choice in modes:
                modes[choice](driver)
            else:
                print_log("Invalid choice, please try again.", "ERROR", is_status=True)
        
        except KeyboardInterrupt:
             print_log("\nShutdown signal received. Please use 'Q' from the menu to quit.", "WARNING", is_status=True)
        except Exception as e:
            print_log(f"A critical error occurred in the control loop: {e}", "ERROR", is_status=True)
            driver.save_screenshot("error_critical_loop.png")

# --- Main Execution ---
async def main():
    # --- DEFAULT CREDENTIALS (REPLACE OR ENTER AT PROMPT) ---
    USERNAME = "your_kick_username" # Placeholder
    PASSWORD = "your_kick_password" # Placeholder
    EMAIL = "your_login_email@domain.com" 
    EMAIL_PASSWORD = "your_email_password" 
    # ----------------------------------------------
    
    print_log("Welcome to KickerzOyaled!", "SUCCESS")

    if USERNAME == "your_kick_username" or PASSWORD == "your_kick_password":
        print_log("Default credentials detected.", "WARNING")
        print_log("Please enter your Kick credentials for this session.", "INFO")
        USERNAME = input(f"{Colors.WARNING}Enter Kick Username/Email: ").strip()
        PASSWORD = input(f"{Colors.WARNING}Enter Kick Password: ").strip()

    channel_name = input(f"{Colors.WARNING}Enter the Kick channel name to join (e.g., xqc): ").lower().strip()
    if not channel_name:
        print_log("Channel name cannot be empty.", "ERROR")
        return

    user_choice = input(f"{Colors.WARNING}Do you want to enter the OTP manually? (y/n): ").lower().strip()
    manual_mode = user_choice == 'y'

    print_log(f"Starting login process for user: {USERNAME}")
    print_log(f"OTP Mode: {'MANUAL' if manual_mode else 'AUTOMATIC (Temp Mail)'}")

    shared_data = {'verification_code': None}
    email_client = None

    if not manual_mode:
        try:
            if EMAIL == "your_login_email@domain.com":
                print_log("Default email detected for automatic mode.", "WARNING")
                EMAIL = input(f"{Colors.WARNING}Enter your temp-mail address (e.g., user@1secmail.com): ").strip()
                EMAIL_PASSWORD = "your_email_password"
            
            email_client = Email()
            email_username_part, email_domain_part = EMAIL.split('@')
            await asyncio.to_thread(email_client.register, username=email_username_part, password=EMAIL_PASSWORD, domain=email_domain_part)
            print_log(f"Logged into email account: {email_client.address}")
            
            listener_callback = lambda msg: asyncio.run(listener(msg, shared_data))
            email_client.start(listener_callback, interval=3)
            print_log("Email listener started.", "SUCCESS")
        except Exception as e:
            print_log(f"Failed to set up automatic email listener: {e}", "ERROR")
            print_log("Switching to MANUAL mode as fallback.", "WARNING")
            manual_mode = True

    task_data = {
        'username': USERNAME, 
        'password': PASSWORD, 
        'shared_data': shared_data,
        'manual_mode': manual_mode,
        'channel_name': channel_name,
    }

    await asyncio.to_thread(interactive_chatter_task, data=task_data)

    if email_client:
        email_client.stop()
        print_log("Email listener stopped.")
    
    print_log("Bot has been shut down.", "SUCCESS")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print_log("\nScript interrupted by user. Exiting.", "WARNING")

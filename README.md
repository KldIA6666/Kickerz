# Kickerz Toolkit (A.I Generated README xd) 🦎

A suite of high-performance, asynchronous tools designed for educational and research purposes related to the Kick streaming platform. This toolkit provides utilities for generating live and VOD views, as well as creating accounts.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> [!WARNING]
> **Disclaimer**: This script is intended for educational and research purposes only. The developer is not responsible for any misuse of this software. By using this script, you agree to use it legally and ethically.

---
## Support The Project

This project is developed and maintained in my free time. If you find these tools useful and wish to support their continued development, please consider donating.

All donations go directly towards funding the resources needed for testing and research, such as dedicated servers and residential proxy plans. Your support helps me go crazy with new ideas and push the boundaries of what's possible.

**Monero (XMR) Address:**
1. ```4362JdtPhfAZbpu95Z2EeJ2fNVsRaxJ8z7sYCsN724z1iLCKMymyDiTTqeqf4p5qnzYE7TifzXkusSiWFr7qykDU7Bv55as```
---

## Developer's Log

*(hUGE shoutut to that homie on reddit for recommending me this library goated individual, anyways this is far easier than i thought i mean my stuff aint THERE yet but im just fucking around and if its that easy to create a script to automate account creatoins then the all in one tool might come sooner rather than later. no way botting services charge you astronomical amounts of money for several hours worth of work LMAO)*

---

## Features

-   **📈 Live View Generation**: Simulate live viewers on a stream using an efficient, websocket-based approach.
-   **🎞️ VOD/Replay View Generation**: Generate views on saved videos (VODs) using a headless browser engine for realistic traffic.
-   **🤖 Automated Account Creation**: Fully automate the Kick account creation and email verification process.
-   **🚀 High Performance**: Built with modern asynchronous Python (`asyncio`, `playwright`, `websockets`) for high concurrency and scalability.
-   **📊 Advanced Terminal UI**: All tools feature a clean, real-time dashboard built with the `rich` library to monitor progress and stats.
-   **🛡️ Proxy Support**: The VOD view generator (`KickerzViewsHybrid.py`) has built-in support for proxies (Direct, Proxy, and Hybrid modes).

## Toolkit Components

This repository contains several specialized scripts. Here is a breakdown of what each one does:

| Script Name               | Purpose                                | Recommended Use                                                                   |
| ------------------------- | -------------------------------------- | --------------------------------------------------------------------------------- |
| `KickerzDos.py`           | Live View Bot                          | **Primary tool for live views.** More advanced than `Uno` with stable/churn workers.  |
| `KickerzViewsHybrid.py`   | VOD / Replay View Bot                  | **Primary tool for VOD views.** Supports direct, proxy, and hybrid connections.     |
| `KickerzDino.py`          | Account Creator                        | Creates and verifies new Kick accounts automatically.                             |
| `KickerzUno.py`           | Live View Bot (Basic)                  | An earlier version of the live view bot. `Dos` is preferred.                        |
| `KickerzViews.py`         | VOD View Bot (Proxy-only)              | An earlier version of the VOD bot. `Hybrid` is more flexible and up-to-date.        |
| `ViewTest.py`             | VOD View Bot (No-Proxy)                | An earlier version of the VOD bot. `Hybrid` can run in direct mode.                 |

---

## Getting Started

Follow these instructions to set up and run the Kickerz toolkit on your system.

### Prerequisites

-   Python 3.9 or higher
-   `pip` (Python package installer)
-   Git

### Installation

1.  **Clone the repository:**
    ```sh
    git clone https://github.com/your-username/your-repo-name.git
    cd your-repo-name
    ```

2.  **Install the required Python packages:**
    Create a file named `requirements.txt` in the project folder and paste the following lines into it:

    ```
    rich
    tls-client
    websockets
    playwright
    botasaurus
    mailtm
    names
    ```

    Now, install all of them with a single command:
    ```sh
    pip install -r requirements.txt
    ```

3.  **Install Playwright browsers:**
    The VOD and account creator tools require headless browser drivers. Install them with this command:
    ```sh
    playwright install
    ```

### Configuration (For VOD Views)

Before running `KickerzViewsHybrid.py` in proxy or hybrid mode, you **must** edit the file and add your proxy credentials:

```python
# --- CONFIGURATION ---
PROXY_TOKEN = "YOUR_PROXY_USERNAME_OR_TOKEN"
PROXY_SERVER = "YOUR_PROXY_IP_ADDRESS:PORT"

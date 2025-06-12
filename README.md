## Prerequisites
- python-telegram-bot
- python-telegram-bot[job-queue]
- requests
- dotenv

## Setup

- Create .env file with following:
```sh
BOT_TOKEN=<API KEY>
```

- You can create telegram bot and get it's API key by [chatting with godfather on telegram](https://telegram.me/BotFather).

## Installation

### pip3 installation
- If pip3 is already present skip this step.

```sh
sudo apt install python3-pip
python3 -m pip install --upgrade pip
```

### Installing virtualenv 
- If virtualenv is already present skip installing.

```sh
pip install virtualenv
```

### Creating new virtual environment

```sh
cd libscraper; virtualenv .venv
source .venv/bin/activate
```

### Installing requirements and running the script

```sh
pip install -r requirements.txt
python3 tbot.py
```

- The bot is now running. Start it with `/start` command and follow intuitive instructions.

# Telegram SelfBot Installation and Setup Guide

This guide will help you install and set up the Telegram SelfBot project completely and step-by-step.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Method 1: Direct Installation](#method-1-direct-installation)
- [Method 2: Using Docker](#method-2-using-docker)
- [Initial Setup](#initial-setup)
- [Starting the SelfBot](#starting-the-selfbot)
- [Setting Up the Web Panel](#setting-up-the-web-panel)
- [Common Troubleshooting](#common-troubleshooting)
- [Frequently Asked Questions](#frequently-asked-questions)

## Prerequisites

Before starting, ensure you have the following installed on your system:

### For Direct Installation:

1. **Python 3.11 or higher**: [Download from Python's official website](https://www.python.org/downloads/)
   - During installation, enable the "Add Python to PATH" option.
   - To verify proper installation: `python --version` or `python3 --version`

2. **PostgreSQL 15 or higher**: [Download PostgreSQL](https://www.postgresql.org/download/)
   - Create a user with full access.
   - Create a database named `selfbot`.

3. **Redis**: [Download Redis](https://redis.io/download)
   - For Windows, you can use [this link](https://github.com/tporadowski/redis/releases).

4. **Telegram API Information**:
   - Visit [my.telegram.org](https://my.telegram.org) and log in with your Telegram account
   - In the API development tools section, create a new application
   - Note the `API_ID` and `API_HASH` values

### For Docker Installation:

1. **Docker**: [Install Docker](https://docs.docker.com/get-docker/)
2. **Docker Compose**: Usually installed with Docker, otherwise [install it](https://docs.docker.com/compose/install/)
3. **Telegram API Information** (same as above)

## Method 1: Direct Installation

### 1. Get the Project

First, clone the project using Git:

```bash
git clone https://github.com/MasterALiReza/w-TelegramSelfBot.git
cd w-TelegramSelfBot
```

If you don't have Git, you can download and extract the project's zip file.

### 2. Create a Python Virtual Environment

To avoid interference with other projects, creating a Python virtual environment is recommended:

#### On Windows:

```powershell
python -m venv venv
.\venv\Scripts\activate
```

#### On Linux/Mac:

```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Use pip to install all required dependencies:

```bash
pip install -r requirements.txt
```

### 4. Set Up the Environment File

Copy the `.env.example` file to `.env` and then edit it with your information:

#### On Windows:

```powershell
copy .env.example .env
```

#### On Linux/Mac:

```bash
cp .env.example .env
```

Then open the `.env` file with a text editor and configure the following values:

```
# Database settings
DB_HOST=localhost
DB_PORT=5432
DB_USER=postgres  # The username you created during PostgreSQL installation
DB_PASSWORD=your_password  # Database password
DB_NAME=selfbot

# Redis settings
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=  # If your Redis has a password, enter it here
REDIS_PREFIX=selfbot:

# Telegram settings
TELEGRAM_API_ID=your_api_id  # API ID from my.telegram.org
TELEGRAM_API_HASH=your_api_hash  # API Hash from my.telegram.org
TELEGRAM_PHONE=+123456789  # Phone number with country code
TELEGRAM_SESSION_NAME=selfbot_session

# API settings
API_SECRET_KEY=your_secret_key_here_min_32_chars  # Create a random key with at least 32 characters
API_TOKEN_EXPIRE_MINUTES=60
```

### 5. Create and Migrate the Database

Create the database structure by running the migration scripts:

#### On Windows:

```powershell
python -m database.migration_manager migrate
```

#### On Linux/Mac:

```bash
python -m database.migration_manager migrate
```

## Method 2: Using Docker

### 1. Get the Project

Clone the project using Git or download and extract its zip file.

### 2. Set Up the Environment File

Copy the `.env.example` file to `.env` and edit it with your information. When using Docker, you don't need to change the database and Redis settings as these services are automatically set up. Just enter your Telegram API information:

```
# Telegram settings (you must change these)
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_PHONE=+123456789
TELEGRAM_SESSION_NAME=selfbot_session

# API settings
API_SECRET_KEY=your_secret_key_here_min_32_chars  # Create a random key
```

### 3. Build and Run Containers

Use Docker Compose to build and run the required containers:

```bash
docker-compose up -d
```

This command will start all the necessary services including the SelfBot, API, web panel, PostgreSQL, and Redis.

### 4. View Logs

To view the execution logs and ensure proper startup:

```bash
docker-compose logs -f
```

## Initial Setup

### Logging into Telegram

When you run the SelfBot for the first time, you'll be prompted to log in to your Telegram account:

1. Enter the verification code sent to your Telegram
2. If your account has two-factor authentication, enter that as well

Session information is stored in a file named `TELEGRAM_SESSION_NAME.session` (according to your .env settings).

### Advanced Settings

For more advanced settings, you can edit the `config/app.json` file. These settings include:

- Default language
- Plugin settings
- API and web configuration
- Admin list

## Starting the SelfBot

### Direct Execution (Without Docker)

#### On Windows:

```powershell
# If using a virtual environment, activate it first
.\venv\Scripts\activate
python main.py
```

#### On Linux/Mac:

```bash
# If using a virtual environment, activate it first
source venv/bin/activate
python main.py
```

### Using Docker

If you're using Docker, the SelfBot is automatically started with the `docker-compose up -d` command. To restart it:

```bash
docker-compose restart selfbot
```

## Setting Up the Web Panel

### Direct Installation

To set up the web panel, you first need to install its prerequisites:

1. Install Node.js (version 16 or higher): [Download Node.js](https://nodejs.org/)
2. Install web panel dependencies:

```bash
cd web
npm install
```

3. Run the web panel in development mode:

```bash
npm run dev
```

Or build the final version:

```bash
npm run build
npm run start
```

### Using Docker

If you're using Docker, the web panel is automatically started on port 3000. You can access it by visiting `http://localhost:3000`.

## Common Troubleshooting

### Database Connection Issues

- Make sure PostgreSQL is running
- Check the database settings in the `.env` file
- Verify that the database user has the necessary permissions

### Redis Connection Issues

- Make sure Redis is running
- If Redis has a password, configure it in the `.env` file

### Telegram Login Issues

- Check that `API_ID` and `API_HASH` are correctly configured in the `.env` file
- Make sure the phone number is entered in the correct format (with country code)
- If you receive a "PHONE_CODE_INVALID" error message, carefully enter the verification code
- If your account has two-factor authentication enabled, enter the two-factor password as well

### Dependency Installation Issues

If you encounter errors while installing dependencies, try these steps:

```bash
# Update pip
python -m pip install --upgrade pip

# Reinstall dependencies
pip install -r requirements.txt
```

### Docker Issues

If you're experiencing Docker issues:

```bash
# Stop and remove containers
docker-compose down

# Clear cache
docker system prune -a

# Rebuild
docker-compose up -d --build
```

## Frequently Asked Questions

### Can I manage multiple Telegram accounts simultaneously?
Yes, for each account, start a separate instance of the SelfBot and change the `TELEGRAM_SESSION_NAME` value in the `.env` file.

### Can the SelfBot run on shared hosting?
No, the SelfBot requires access to system resources like database and Redis, which are usually restricted on shared hosting. Using a VPS or cloud services is recommended.

### Is using the SelfBot safe?
The SelfBot is designed with full encryption of sensitive data, but it's recommended to always use it for personal purposes and not share your account information.

### Can the SelfBot run on Raspberry Pi?
Yes, with proper prerequisites installation and configuration, you can run the SelfBot on a Raspberry Pi.

### How much system resources does the SelfBot consume?
Resource consumption depends on the number of active plugins and the number of conversations. On average, a minimum of 512MB RAM and 1GB disk space is required.
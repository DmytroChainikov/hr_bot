#!/bin/bash

echo "Starting HR Bot..."
echo ""

# Activate virtual environment
if [ -f venv/bin/activate ]; then
    source venv/bin/activate
else
    echo "Virtual environment not found!"
    echo "Please run: python -m venv venv"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    echo ".env file not found!"
    echo "Please copy .env.example to .env and configure it"
    exit 1
fi

# Run the bot
python main.py

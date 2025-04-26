#!/bin/bash
# Script to setup the project environment

set -e

# Echo with color
info() {
    echo -e "\e[34m[INFO] $1\e[0m"
}

success() {
    echo -e "\e[32m[SUCCESS] $1\e[0m"
}

error() {
    echo -e "\e[31m[ERROR] $1\e[0m"
}

warning() {
    echo -e "\e[33m[WARNING] $1\e[0m"
}

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    warning "Poetry not found. Installing Poetry..."
    curl -sSL https://install.python-poetry.org | python3 -
fi

# Check if Python 3.10 or higher is installed
if ! command -v python3 &> /dev/null; then
    error "Python 3 not found. Please install Python 3.10 or higher."
    exit 1
fi

# Get Python version
python_version=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
python_version_major=$(echo $python_version | cut -d. -f1)
python_version_minor=$(echo $python_version | cut -d. -f2)

# Check Python version
if [ "$python_version_major" -lt 3 ] || ([ "$python_version_major" -eq 3 ] && [ "$python_version_minor" -lt 10 ]); then
    error "Python 3.10 or higher is required. Found Python $python_version."
    exit 1
fi

success "Found Python $python_version."

# Create directories if they don't exist
info "Creating necessary directories..."
mkdir -p logs

# Install project dependencies with Poetry
info "Installing project dependencies..."
poetry install

# Create .env file from example if it doesn't exist
if [ ! -f .env ]; then
    info "Creating .env file from example..."
    cp .env.example .env
    warning "Remember to update your .env file with appropriate values!"
fi

# Check if Ollama is installed
if ! command -v ollama &> /dev/null; then
    warning "Ollama not found. Please install Ollama manually."
    echo "Visit https://ollama.ai/ for installation instructions."
else
    success "Found Ollama."
    # Check if the required model is available
    model=$(grep OLLAMA_MODEL .env | cut -d= -f2 | tr -d '"')
    info "Checking for required Ollama model: $model"
    if ! ollama list | grep -q "$model"; then
        warning "Model $model not found. Attempting to download..."
        ollama pull $model
    else
        success "Model $model is already downloaded."
    fi
fi

# Create SQLite database
info "Initializing database..."
poetry run python -c "
from sqlalchemy import create_engine
from sqlalchemy.sql import text
import os
from dotenv import load_dotenv

load_dotenv()
db_url = os.getenv('DATABASE_URL')
if db_url:
    engine = create_engine(db_url)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('Database initialized successfully.')
else:
    print('DATABASE_URL not found in .env file.')
"

success "Setup completed! You can now start using the LLM Trader for MT5."
echo "To activate the virtual environment, run: poetry shell"
echo "To start the dashboard: poetry run python -m llm_trader_mt5.dashboard.app" 
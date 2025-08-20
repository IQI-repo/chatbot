#!/bin/bash

# This script runs when the application starts on Render
# It will start the FastAPI server and also set up the scheduler for refreshing Qdrant collections

echo "Starting application on Render..."

# Set up Python environment
echo "Setting up Python environment..."
python -m pip install --upgrade pip
pip install -r requirements.txt

# Run the refresh script once at startup to ensure collections are up-to-date
echo "Running initial Qdrant collections refresh..."
python refresh_qdrant_collections.py

# Start the scheduler in the background
echo "Starting scheduler for periodic Qdrant collections refresh..."
python -m src.scheduler &

# Start the FastAPI server
echo "Starting FastAPI server..."
exec uvicorn api:app --host 0.0.0.0 --port $PORT

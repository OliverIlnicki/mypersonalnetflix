"""
Video Preview Application - Main Launcher
=========================================

Overview:
---------
This script serves as the primary entry point for the Video Preview Application.
It handles the initialization and launching of both frontend and backend servers,
with configuration management and command-line options for flexibility.

The application allows for processing and viewing video previews, supporting both
local videos and YouTube sources, generating thumbnails and preview clips.

Features:
---------
* Configurable through both config.json and command-line arguments
* Support for environment variable overrides
* Flexible deployment options (run both servers, backend-only, or frontend-only)
* Thread-based concurrent server execution

Usage Examples:
--------------
# Run both frontend and backend with default settings
python main.py

# Run only the backend server on port 9000
python main.py --backend-only --backend-port 9000

# Run only the frontend, connecting to a remote API
python main.py --frontend-only --api-url https://remote-api.example.com

Configuration Hierarchy:
----------------------
1. Default values (defined in load_config)
2. Values from config.json
3. Command-line arguments
4. Environment variables (highest priority)
"""
import os
import sys
import argparse
import subprocess
import time
import json
from threading import Thread


def load_config():
    """
    Load application configuration from config.json file.
    
    This function tries to read configuration from a config.json file in the same
    directory as this script. If the file doesn't exist, it creates one with default 
    values. If there's an error reading the file, it falls back to defaults.
    
    Returns:
        dict: Configuration dictionary with the following keys:
            - backend_port: Port number for the backend API server
            - frontend_port: Port number for the frontend web server
            - data_dir: Directory path for storing/accessing video data
            - api_url: URL for the backend API (optional, defaults to None)
    """
    # Default configuration values
    default_config = {
        "backend_port": 8000,
        "frontend_port": 8001,
        "data_dir": "./data",
        "api_url": None
    }
    
    # Determine the absolute path to the config file
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    
    # Try to load from config file
    try:
        if os.path.exists(config_path):
            with open(config_path, 'r') as f:
                return json.load(f)
        else:
            # Create default config file if it doesn't exist
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=4)
            print(f"Created new config file at {config_path} with default values")
    except Exception as e:
        print(f"Warning: Error with config file: {e}. Using defaults.")
    
    return default_config


def run_backend(port):
    """
    Launch the backend API server.
    
    This function starts the backend API server that handles video processing,
    database operations, and serving video preview data.
    
    Args:
        port (int): The port number on which the backend API will listen
    """
    print(f"Starting backend API on port {port}...")
    os.environ["PORT"] = str(port)
    # Use the correct path to backend_api.py in the backend directory
    backend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "backend", "backend_api.py")
    subprocess.run([sys.executable, backend_path])


def run_frontend(port, api_url):
    """
    Launch the frontend web server.
    
    This function starts the frontend web server that provides the user interface
    for browsing and viewing video previews. It connects to the backend API.
    
    Args:
        port (int): The port number on which the frontend server will listen
        api_url (str): The URL where the backend API can be reached
    """
    print(f"Starting frontend on port {port} (connecting to API at {api_url})...")
    os.environ["PORT"] = str(port)
    os.environ["API_URL"] = api_url
    # Use the correct path to frontend_app.py in the frontend directory
    frontend_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                "frontend", "frontend_app.py")
    subprocess.run([sys.executable, frontend_path])


def main():
    """
    Main application entry point.
    
    This function handles command-line argument parsing, configuration loading,
    and launches the appropriate server components based on the specified options.
    
    The function supports three modes of operation:
    1. Run both backend and frontend servers (default)
    2. Run only the backend server (--backend-only)
    3. Run only the frontend server (--frontend-only)
    
    Configuration values are loaded with the following priority:
    1. Default values
    2. Values from config.json
    3. Command-line arguments
    4. Environment variables (highest priority)
    """
    # Load config first
    config = load_config()
    
    # Define command-line arguments with defaults from config
    parser = argparse.ArgumentParser(description="Video Preview Application")
    parser.add_argument("--backend-port", type=int, default=config.get("backend_port"), 
                       help=f"Port for the backend API server (default: {config.get('backend_port')})")
    parser.add_argument("--frontend-port", type=int, default=config.get("frontend_port"), 
                       help=f"Port for the frontend server (default: {config.get('frontend_port')})")
    parser.add_argument("--data-dir", type=str, default=config.get("data_dir"), 
                       help=f"Directory containing video data (default: {config.get('data_dir')})")
    parser.add_argument("--backend-only", action="store_true", 
                       help="Run only the backend server")
    parser.add_argument("--frontend-only", action="store_true", 
                       help="Run only the frontend server")
    parser.add_argument("--api-url", type=str, default=config.get("api_url"), 
                       help="URL for the backend API (for frontend-only mode)")
    
    args = parser.parse_args()
    
    # Override config with environment variables (highest priority)
    if "BACKEND_PORT" in os.environ:
        args.backend_port = int(os.environ["BACKEND_PORT"])
    if "FRONTEND_PORT" in os.environ:
        args.frontend_port = int(os.environ["FRONTEND_PORT"])
    if "DATA_DIR" in os.environ:
        args.data_dir = os.environ["DATA_DIR"]
    if "API_URL" in os.environ:
        args.api_url = os.environ["API_URL"]
    
    # Convert relative data directory to absolute path
    if not os.path.isabs(args.data_dir):
        args.data_dir = os.path.abspath(args.data_dir)
    
    # Set data directory as environment variable for child processes
    os.environ["DATA_DIR"] = args.data_dir
    
    # Backend-only mode
    if args.backend_only:
        run_backend(args.backend_port)
        return
    
    # Frontend-only mode
    if args.frontend_only:
        api_url = args.api_url or f"http://localhost:{args.backend_port}"
        run_frontend(args.frontend_port, api_url)
        return
    
    # Run both (default mode)
    api_url = args.api_url or f"http://localhost:{args.backend_port}"
    
    # Start backend in a separate thread
    backend_thread = Thread(target=run_backend, args=(args.backend_port,))
    backend_thread.daemon = True
    backend_thread.start()
    
    # Give the backend a moment to start up
    print("Waiting for backend to start...")
    time.sleep(2)
    
    # Run frontend (blocking call in the main thread)
    run_frontend(args.frontend_port, api_url)


if __name__ == "__main__":
    main()
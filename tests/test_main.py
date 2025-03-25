import os
import sys
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
import main


@pytest.fixture
def temp_config():
    """Create a temporary config file and environment for testing"""
    # Create a temporary directory
    import tempfile
    temp_dir = tempfile.mkdtemp()
    
    # Save the original environment variables
    original_env = {}
    for var in ["BACKEND_PORT", "FRONTEND_PORT", "DATA_DIR", "API_URL"]:
        if var in os.environ:
            original_env[var] = os.environ[var]
            del os.environ[var]
    
    # Create a config file path in the temporary directory
    config_path = os.path.join(temp_dir, "config.json")
    
    # Patch the path to the config file
    with patch("main.os.path.join", return_value=config_path):
        yield temp_dir, config_path
    
    # Restore the original environment variables
    for var, val in original_env.items():
        os.environ[var] = val
    
    # Remove vars that weren't originally set
    for var in ["BACKEND_PORT", "FRONTEND_PORT", "DATA_DIR", "API_URL"]:
        if var not in original_env and var in os.environ:
            del os.environ[var]
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def test_load_config_no_file(temp_config):
    """Test loading config when no file exists"""
    temp_dir, config_path = temp_config
    
    # Call the function
    config = main.load_config()
    
    # Check the result
    assert config["backend_port"] == 8000
    assert config["frontend_port"] == 8001
    assert config["data_dir"] == "./data"
    assert config["api_url"] is None
    
    # Check that the config file was created
    assert os.path.exists(config_path)
    
    # Check the content of the config file
    with open(config_path, 'r') as f:
        saved_config = json.load(f)
    
    assert saved_config["backend_port"] == 8000
    assert saved_config["frontend_port"] == 8001


def test_load_config_existing_file(temp_config):
    """Test loading config from an existing file"""
    temp_dir, config_path = temp_config
    
    # Create a custom config file
    custom_config = {
        "backend_port": 9000,
        "frontend_port": 9001,
        "data_dir": "/custom/data/dir",
        "api_url": "http://custom-api.example.com"
    }
    
    with open(config_path, 'w') as f:
        json.dump(custom_config, f)
    
    # Call the function
    config = main.load_config()
    
    # Check the result
    assert config["backend_port"] == 9000
    assert config["frontend_port"] == 9001
    assert config["data_dir"] == "/custom/data/dir"
    assert config["api_url"] == "http://custom-api.example.com"


def test_load_config_error(temp_config):
    """Test handling errors when loading config"""
    temp_dir, config_path = temp_config
    
    # Create an invalid config file
    with open(config_path, 'w') as f:
        f.write("This is not valid JSON")
    
    # Call the function
    config = main.load_config()
    
    # Check that it falls back to defaults
    assert config["backend_port"] == 8000
    assert config["frontend_port"] == 8001
    assert config["data_dir"] == "./data"
    assert config["api_url"] is None


@patch("main.subprocess.run")
def test_run_backend(mock_subprocess_run):
    """Test running the backend server"""
    # Call the function
    main.run_backend(9000)
    
    # Check that subprocess.run was called with the correct arguments
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    
    # Check that it's running python with the backend_api.py script
    assert call_args[0] == sys.executable
    assert call_args[1].endswith("backend_api.py")
    
    # Check that the environment was set
    assert os.environ["PORT"] == "9000"


@patch("main.subprocess.run")
def test_run_frontend(mock_subprocess_run):
    """Test running the frontend server"""
    # Call the function
    main.run_frontend(9001, "http://localhost:9000")
    
    # Check that subprocess.run was called with the correct arguments
    mock_subprocess_run.assert_called_once()
    call_args = mock_subprocess_run.call_args[0][0]
    
    # Check that it's running python with the frontend_app.py script
    assert call_args[0] == sys.executable
    assert call_args[1].endswith("frontend_app.py")
    
    # Check that the environment was set
    assert os.environ["PORT"] == "9001"
    assert os.environ["API_URL"] == "http://localhost:9000"


@patch("main.run_backend")
@patch("main.run_frontend")
@patch("main.Thread")
@patch("main.time.sleep")
@patch("main.load_config")
@patch("main.argparse.ArgumentParser")
def test_main_both_servers(mock_argparser, mock_load_config, mock_sleep, mock_thread, mock_run_frontend, mock_run_backend):
    """Test running both backend and frontend servers"""
    # Setup mocks
    mock_load_config.return_value = {
        "backend_port": 9000,  # Updated to match what's being used
        "frontend_port": 8001,
        "data_dir": "./data",
        "api_url": None
    }
    
    mock_args = MagicMock()
    mock_args.backend_port = 9000  # Match this value with what's returned
    mock_args.frontend_port = 8001
    mock_args.data_dir = "./data"
    mock_args.backend_only = False
    mock_args.frontend_only = False
    mock_args.api_url = None
    
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparser.return_value = mock_parser
    
    # Call the main function
    main.main()
    
    # Check that backend was started in a thread
    mock_thread.assert_called_once_with(target=mock_run_backend, args=(9000,))
    mock_thread.return_value.daemon = True
    mock_thread.return_value.start.assert_called_once()
    
    # Check that there was a delay for backend startup
    mock_sleep.assert_called_once_with(2)
    
    # Check that frontend was started directly with the correct URL
    mock_run_frontend.assert_called_once_with(8001, "http://localhost:9000")


@patch("main.run_backend")
@patch("main.run_frontend")
@patch("main.load_config")
@patch("main.argparse.ArgumentParser")
def test_main_backend_only(mock_argparser, mock_load_config, mock_run_frontend, mock_run_backend):
    """Test running only the backend server"""
    # Setup mocks
    mock_load_config.return_value = {
        "backend_port": 8000,
        "frontend_port": 8001,
        "data_dir": "./data",
        "api_url": None
    }
    
    mock_args = MagicMock()
    mock_args.backend_port = 8000
    mock_args.frontend_port = 8001
    mock_args.data_dir = "./data"
    mock_args.backend_only = True
    mock_args.frontend_only = False
    mock_args.api_url = None
    
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparser.return_value = mock_parser
    
    # Call the main function
    main.main()
    
    # Check that only backend was started
    mock_run_backend.assert_called_once_with(8000)
    mock_run_frontend.assert_not_called()


@patch("main.run_backend")
@patch("main.run_frontend")
@patch("main.load_config")
@patch("main.argparse.ArgumentParser")
def test_main_frontend_only(mock_argparser, mock_load_config, mock_run_frontend, mock_run_backend):
    """Test running only the frontend server"""
    # Setup mocks
    mock_load_config.return_value = {
        "backend_port": 9000,  # Update this
        "frontend_port": 8001,
        "data_dir": "./data",
        "api_url": None
    }

    mock_args = MagicMock()
    mock_args.backend_port = 9000
    mock_args.frontend_port = 8001
    mock_args.data_dir = "./data"
    mock_args.backend_only = False
    mock_args.frontend_only = True
    mock_args.api_url = "http://localhost:9000"  # Update this

    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparser.return_value = mock_parser

    # Call the main function
    main.main()

    # Check that only frontend was started
    mock_run_backend.assert_not_called()
    mock_run_frontend.assert_called_once_with(8001, "http://localhost:9000")


@patch("main.load_config")
@patch("main.argparse.ArgumentParser")
def test_main_env_vars_priority(mock_argparser, mock_load_config):
    """Test that environment variables take priority over config file and args"""
    # Setup mocks
    mock_load_config.return_value = {
        "backend_port": 8000,
        "frontend_port": 8001,
        "data_dir": "./data",
        "api_url": None
    }
    
    mock_args = MagicMock()
    mock_args.backend_port = 8000
    mock_args.frontend_port = 8001
    mock_args.data_dir = "./data"
    mock_args.backend_only = True  # We'll just check args processing, not execution
    mock_args.frontend_only = False
    mock_args.api_url = None
    
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparser.return_value = mock_parser
    
    # Set environment variables
    os.environ["BACKEND_PORT"] = "9000"
    os.environ["FRONTEND_PORT"] = "9001"
    os.environ["DATA_DIR"] = "/env/data/dir"
    os.environ["API_URL"] = "http://env-api.example.com"
    
    # Call the main function with a mock to prevent actual execution
    with patch("main.run_backend"):
        main.main()
    
    # Check that environment variables were applied to args
    assert mock_args.backend_port == 9000
    assert mock_args.frontend_port == 9001
    assert mock_args.data_dir == "/env/data/dir"
    assert mock_args.api_url == "http://env-api.example.com"
    
    # Clean up
    del os.environ["BACKEND_PORT"]
    del os.environ["FRONTEND_PORT"]
    del os.environ["DATA_DIR"]
    del os.environ["API_URL"]

import os
import sys
import json
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, call
from backend.videos2db import (
    main, 
    _run_query_mode,
    _run_local_dir_mode,
    _run_single_url_mode,
    _run_links_file_mode,
    _print_video_summary
)

@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_video_processor():
    """Create a mock VideoProcessor"""
    with patch("backend.videos2db.VideoProcessor") as mock:
        mock_instance = MagicMock()
        mock.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def sample_links_file(temp_dir):
    """Create a sample file with video links"""
    file_path = os.path.join(temp_dir, "links.txt")
    with open(file_path, 'w') as f:
        f.write("https://www.youtube.com/watch?v=dQw4w9WgXcQ\n")
        f.write("https://youtu.be/ABC123\n")
        f.write("file:///path/to/video.mp4\n")
    return file_path


@patch("backend.videos2db.argparse.ArgumentParser")
@patch("backend.videos2db.VideoProcessor")
def test_main_query_mode(mock_processor_class, mock_argparse, temp_dir):
    """Test main function in query mode"""
    # Set up mocks
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor

    mock_args = MagicMock()
    mock_args.query = True
    mock_args.links_file = None
    mock_args.url = None
    mock_args.local_dir = None
    mock_args.output = temp_dir  # Use temp_dir instead of "/test/output"
    mock_args.user = "test_user"
    mock_args.filter_user = "filter_user"
    mock_args.filter_year = 2023
    mock_args.filter_source = "youtube"

    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparse.return_value = mock_parser

    # Create necessary directories
    os.makedirs(os.path.join(temp_dir, "filter_user"), exist_ok=True)
    
    # Mock the run mode function
    with patch("backend.videos2db._run_query_mode") as mock_run_query:
        # Call the main function
        main()

        # Verify the correct run mode was called
        mock_run_query.assert_called_once()

@patch("backend.videos2db.argparse.ArgumentParser")
@patch("backend.videos2db.VideoProcessor")
def test_main_local_dir_mode(mock_processor_class, mock_argparse):
    """Test main function in local directory mode"""
    # Set up mocks
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor
    
    mock_args = MagicMock()
    mock_args.query = False
    mock_args.links_file = None
    mock_args.url = None
    mock_args.local_dir = "/test/videos"
    mock_args.output = "/test/output"
    mock_args.user = "test_user"
    
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparse.return_value = mock_parser
    
    # Mock the run mode function
    with patch("backend.videos2db._run_local_dir_mode") as mock_run_local:
        # Call the main function
        main()
        
        # Check that the correct mode was called
        mock_run_local.assert_called_once_with(mock_processor, mock_args)


@patch("backend.videos2db.argparse.ArgumentParser")
@patch("backend.videos2db.VideoProcessor")
def test_main_single_url_mode(mock_processor_class, mock_argparse):
    """Test main function in single URL mode"""
    # Set up mocks
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor
    
    mock_args = MagicMock()
    mock_args.query = False
    mock_args.links_file = None
    mock_args.url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    mock_args.local_dir = None
    mock_args.output = "/test/output"
    mock_args.user = "test_user"
    
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparse.return_value = mock_parser
    
    # Mock the run mode function
    with patch("backend.videos2db._run_single_url_mode") as mock_run_single:
        # Call the main function
        main()
        
        # Check that the correct mode was called
        mock_run_single.assert_called_once_with(mock_processor, mock_args)


@patch("backend.videos2db.argparse.ArgumentParser")
@patch("backend.videos2db.VideoProcessor")
def test_main_links_file_mode(mock_processor_class, mock_argparse):
    """Test main function in links file mode"""
    # Set up mocks
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor
    
    mock_args = MagicMock()
    mock_args.query = False
    mock_args.links_file = "/test/links.txt"
    mock_args.url = None
    mock_args.local_dir = None
    mock_args.output = "/test/output"
    mock_args.user = "test_user"
    
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_argparse.return_value = mock_parser
    
    # Mock the run mode function
    with patch("backend.videos2db._run_links_file_mode") as mock_run_links:
        # Call the main function
        main()
        
        # Check that the correct mode was called
        mock_run_links.assert_called_once_with(mock_processor, mock_args, "/test/output")


@patch("backend.videos2db.argparse.ArgumentParser")
@patch("backend.videos2db.VideoProcessor")
def test_main_no_input(mock_processor_class, mock_argparse):
    """Test main function with no input source"""
    # Set up mocks
    mock_processor = MagicMock()
    mock_processor_class.return_value = mock_processor
    
    mock_args = MagicMock()
    mock_args.query = False
    mock_args.links_file = None
    mock_args.url = None
    mock_args.local_dir = None
    mock_args.output = "/test/output"
    mock_args.user = "test_user"
    
    mock_parser = MagicMock()
    mock_parser.parse_args.return_value = mock_args
    mock_parser.error = MagicMock()
    mock_argparse.return_value = mock_parser
    
    # Call the main function
    main()
    
    # Check that an error was raised
    mock_parser.error.assert_called_once_with("Either 'links_file', '--url', '--local-dir' or '--query' must be provided")


@patch("backend.videos2db.print")
def test_run_query_mode(mock_print, mock_video_processor, temp_dir):
    """Test running in query mode"""
    # Set up mock args
    mock_args = MagicMock()
    mock_args.filter_user = "test_user"
    mock_args.filter_year = 2023
    mock_args.filter_source = "youtube"
    
    # Set up mock results
    mock_video_processor.query_database.return_value = [
        {
            "id": 1,
            "user": "test_user",
            "source": "youtube",
            "title": "Test Video 1",
            "upload_year": 2023,
            "url": "https://www.youtube.com/watch?v=ABC123",
            "thumb_path": "test_user/thumbnails/test1.jpg",
            "vid_preview_path": "test_user/previews/test1.gif"
        },
        {
            "id": 2,
            "user": "test_user",
            "source": "youtube",
            "title": "Test Video 2",
            "upload_year": 2023,
            "url": "https://www.youtube.com/watch?v=DEF456",
            "thumb_path": "test_user/thumbnails/test2.jpg",
            "vid_preview_path": "test_user/previews/test2.gif"
        }
    ]
    
    # Create user directory
    user_dir = os.path.join(temp_dir, "test_user")
    os.makedirs(user_dir, exist_ok=True)
    
    # Call the function
    _run_query_mode(mock_video_processor, mock_args, temp_dir)
    
    # Check that query_database was called
    mock_video_processor.query_database.assert_called_once_with("test_user", 2023, "youtube")
    
    # Check that results were printed
    assert mock_print.call_count > 0
    
    # Check that results were saved to JSON
    json_path = os.path.join(user_dir, "filtered_user_test_user_year_2023_source_youtube.json")
    assert os.path.exists(json_path)
    
    # Check the JSON content
    with open(json_path, 'r') as f:
        saved_data = json.load(f)
    
    assert len(saved_data) == 2
    assert saved_data[0]["title"] == "Test Video 1"
    assert saved_data[1]["title"] == "Test Video 2"


def test_run_local_dir_mode(mock_video_processor):
    """Test running in local directory mode"""
    # Set up mock args
    mock_args = MagicMock()
    mock_args.local_dir = "/test/local/videos"
    mock_args.user = "test_user"

    # Set up mock results with all required keys
    mock_video_processor.process_local_directory.return_value = [
        {
            "id": 1, 
            "title": "Local Video 1",
            "user": "test_user",
            "source": "local",
            "upload_year": 2023,
            "url": "/path/to/video1.mp4",
            "thumb_path": "thumbnails/video1.jpg",
            "vid_preview_path": "previews/video1.gif"
        },
        {
            "id": 2, 
            "title": "Local Video 2",
            "user": "test_user",
            "source": "local",
            "upload_year": 2022,
            "url": "/path/to/video2.mp4",
            "thumb_path": "thumbnails/video2.jpg",
            "vid_preview_path": "previews/video2.gif"
        }
    ]

    # Mock _print_video_summary to avoid real printing
    with patch("backend.videos2db._print_video_summary"):
        _run_local_dir_mode(mock_video_processor, mock_args)

    # Verify the correct methods were called
    mock_video_processor.process_local_directory.assert_called_once_with(
        mock_args.local_dir, mock_args.user
    )
    mock_video_processor.save_results.assert_called_once()


def test_run_single_url_mode(mock_video_processor):
    """Test running in single URL mode"""
    # Set up mock args
    mock_args = MagicMock()
    mock_args.url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    mock_args.user = "test_user"

    # Set up mock results with all required keys including upload_year
    mock_video_processor.process_url.return_value = {
        "id": 1,
        "user": "test_user",
        "source": "youtube",
        "title": "Test Video",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "thumb_path": "test_user/thumbnails/test.jpg",
        "vid_preview_path": "test_user/previews/test.gif",
        "upload_year": 2022  # Add the missing upload_year
    }

    # Mock print to avoid real printing
    with patch("builtins.print"):
        _run_single_url_mode(mock_video_processor, mock_args)

    # Verify the correct methods were called
    mock_video_processor.process_url.assert_called_once_with(
        mock_args.url, mock_args.user
    )
    mock_video_processor.save_results.assert_called_once()

def test_run_links_file_mode(mock_video_processor, sample_links_file, temp_dir):
    """Test running in links file mode"""
    # Set up mock args
    mock_args = MagicMock()
    mock_args.links_file = sample_links_file
    mock_args.user = "test_user"

    # Set up mock results with all required keys
    mock_video_processor.process_links_file.return_value = [
        {
            "id": 1, 
            "title": "Video 1",
            "user": "test_user",
            "source": "youtube",
            "upload_year": 2023,
            "url": "https://example.com/video1",
            "thumb_path": "thumbnails/video1.jpg",
            "vid_preview_path": "previews/video1.gif"
        },
        {
            "id": 2, 
            "title": "Video 2",
            "user": "test_user",
            "source": "local",
            "upload_year": 2022,
            "url": "/path/to/video2.mp4",
            "thumb_path": "thumbnails/video2.jpg",
            "vid_preview_path": "previews/video2.gif"
        }
    ]

    # Mock _print_video_summary to avoid real printing
    with patch("backend.videos2db._print_video_summary"):
        _run_links_file_mode(mock_video_processor, mock_args, temp_dir)

    # Verify the correct methods were called
    mock_video_processor.process_links_file.assert_called_once_with(
        mock_args.links_file, mock_args.user
    )
    mock_video_processor.save_results.assert_called_once()



@patch("backend.videos2db.print")
def test_print_video_summary(mock_print):
    """Test printing video summary"""
    # Create test data
    results = [
        {
            "user": "test_user",
            "source": "youtube",
            "title": "Test Video 1",
            "url": "https://www.youtube.com/watch?v=ABC123",
            "thumb_path": "test_user/thumbnails/test1.jpg",
            "vid_preview_path": "test_user/previews/test1.gif",
            "upload_year": 2023
        },
        {
            "user": "test_user",
            "source": "local",
            "title": "Test Video 2",
            "url": "file:///path/to/video.mp4",
            "thumb_path": "test_user/thumbnails/test2.jpg",
            "vid_preview_path": "test_user/previews/test2.gif",
            "upload_year": 2022
        }
    ]
    
    # Call the function
    _print_video_summary(results)
    
    # Check that print was called multiple times
    assert mock_print.call_count > 5
    
    # Check some of the print calls
    mock_print.assert_any_call("\nProcessed Video Summary:")
    
    # We can't easily check all print calls due to newlines and formatting,
    # but we can verify that key information was printed
    printed_text = "".join(str(call.args[0]) for call in mock_print.call_args_list if call.args)
    assert "Test Video 1" in printed_text
    assert "Test Video 2" in printed_text
    assert "youtube" in printed_text
    assert "local" in printed_text
    assert "2023" in printed_text
    assert "2022" in printed_text
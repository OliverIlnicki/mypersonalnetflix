import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the src directory to the path
sys.path.append(str(Path(__file__).parent.parent / "backend" / "src"))

# Import the youtube_url_checker module
from youtube_url_checker import (
    is_valid_youtube_url,
    check_youtube_video_accessible
)


def test_is_valid_youtube_url():
    """Test URL format validation for YouTube URLs"""
    # Valid YouTube URLs
    assert is_valid_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("http://www.youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("youtube.com/watch?v=dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("https://youtu.be/dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("http://youtu.be/dQw4w9WgXcQ") is True
    assert is_valid_youtube_url("youtu.be/dQw4w9WgXcQ") is True
    
    # Valid URLs with additional parameters
    assert is_valid_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=30s") is True
    assert is_valid_youtube_url("https://youtu.be/dQw4w9WgXcQ?t=30") is True
    
    # Invalid URLs
    assert is_valid_youtube_url("https://www.example.com") is False
    assert is_valid_youtube_url("https://www.youtube.com") is False
    assert is_valid_youtube_url("https://www.youtube.com/playlist?list=123") is False
    assert is_valid_youtube_url("invalid_string") is False
    assert is_valid_youtube_url("") is False


@patch("youtube_url_checker.requests.head")
@patch("youtube_url_checker.YouTube")
def test_check_youtube_video_accessible_success(mock_youtube, mock_head):
    """Test checking accessibility of a valid YouTube video"""
    # Mock the requests.head response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response
    
    # Mock the YouTube object
    mock_yt = MagicMock()
    mock_yt.check_availability.return_value = None
    mock_yt.title = "Test Video"
    mock_youtube.return_value = mock_yt
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is True
    assert message == "Video is accessible"
    
    # Verify the mocks were called
    mock_head.assert_called_once_with(
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ", 
        timeout=10, 
        allow_redirects=True
    )
    mock_youtube.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    mock_yt.check_availability.assert_called_once()


@patch("youtube_url_checker.requests.head")
def test_check_youtube_video_accessible_invalid_url(mock_head):
    """Test checking accessibility of an invalid YouTube URL"""
    # Call the function with an invalid URL
    accessible, message = check_youtube_video_accessible("https://www.example.com")
    
    # Check the result
    assert accessible is False
    assert message == "Invalid YouTube URL format"
    
    # Verify the mock was not called
    mock_head.assert_not_called()


@patch("youtube_url_checker.requests.head")
def test_check_youtube_video_accessible_http_error(mock_head):
    """Test checking accessibility when HTTP error occurs"""
    # Mock the requests.head response to return a 404
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_head.return_value = mock_response
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is False
    assert message == "HTTP Error 404"


@patch("youtube_url_checker.requests.head")
def test_check_youtube_video_accessible_request_exception(mock_head):
    """Test checking accessibility when a request exception occurs"""
    # Mock the requests.head to raise an exception
    mock_head.side_effect = Exception("Connection failed")
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is False
    assert "Connection failed" in message


@patch("youtube_url_checker.requests.head")
@patch("youtube_url_checker.YouTube")
def test_check_youtube_video_unavailable(mock_youtube, mock_head):
    """Test checking accessibility of an unavailable YouTube video"""
    # Mock the requests.head response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response
    
    # Mock the YouTube object to raise VideoUnavailable
    from pytubefix.exceptions import VideoUnavailable
    mock_youtube.return_value.check_availability.side_effect = VideoUnavailable("Video is unavailable")
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is False
    assert message == "Video unavailable (deleted or private)"


@patch("youtube_url_checker.requests.head")
@patch("youtube_url_checker.YouTube")
def test_check_youtube_video_private(mock_youtube, mock_head):
    """Test checking accessibility of a private YouTube video"""
    # Mock the requests.head response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response
    
    # Mock the YouTube object to raise VideoPrivate
    from pytubefix.exceptions import VideoPrivate
    mock_youtube.return_value.check_availability.side_effect = VideoPrivate("Video is private")
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is False
    assert message == "Video is private"


@patch("youtube_url_checker.requests.head")
@patch("youtube_url_checker.YouTube")
def test_check_youtube_video_age_restricted(mock_youtube, mock_head):
    """Test checking accessibility of an age-restricted YouTube video"""
    # Mock the requests.head response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response
    
    # Mock the YouTube object with check_availability passing but title raising an exception
    mock_yt = MagicMock()
    mock_yt.check_availability.return_value = None
    mock_youtube.return_value = mock_yt
    
    # Setting title property to raise exception for age restriction
    type(mock_yt).title = property(side_effect=Exception("age restricted"))
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is False
    assert message == "Age-restricted content (login required)"

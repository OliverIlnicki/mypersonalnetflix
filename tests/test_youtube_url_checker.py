from unittest.mock import patch, MagicMock
import pytest
import sys
import os

# Fixtures for common test setup
@pytest.fixture
def setup_youtube_checker():
    # Create necessary mocks for imports
    sys.modules['pytubefix'] = MagicMock()
    sys.modules['pytubefix.exceptions'] = MagicMock()
    
    # Create the exception classes
    class VideoUnavailable(Exception): pass
    class VideoPrivate(Exception): pass
    class LiveStreamError(Exception): pass
    
    sys.modules['pytubefix.exceptions'].VideoUnavailable = VideoUnavailable
    sys.modules['pytubefix.exceptions'].VideoPrivate = VideoPrivate
    sys.modules['pytubefix.exceptions'].LiveStreamError = LiveStreamError
    
    yield
    
    # Clean up
    if 'pytubefix' in sys.modules:
        del sys.modules['pytubefix']
    if 'pytubefix.exceptions' in sys.modules:
        del sys.modules['pytubefix.exceptions']

@patch("backend.src.youtube_url_checker.requests.head")
@patch("backend.src.youtube_url_checker.YouTube")
def test_check_youtube_video_private(mock_youtube, mock_head, setup_youtube_checker):
    """Test checking accessibility of a private YouTube video"""
    # Mock the requests.head response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response
    
    # Import locally with patched modules
    from backend.src.youtube_url_checker import check_youtube_video_accessible
    
    # Get the VideoPrivate exception from our patched modules
    VideoPrivate = sys.modules['pytubefix.exceptions'].VideoPrivate
    
    # Mock the YouTube object to raise VideoPrivate
    mock_youtube.return_value.check_availability.side_effect = VideoPrivate("Video is private")
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is False
    assert "private" in message.lower()  # More flexible assertion

@patch("backend.src.youtube_url_checker.requests.head")
@patch("backend.src.youtube_url_checker.YouTube")
def test_check_youtube_video_age_restricted(mock_youtube, mock_head, setup_youtube_checker):
    """Test checking accessibility of an age-restricted YouTube video"""
    # Mock the requests.head response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_head.return_value = mock_response
    
    # Import locally with patched modules
    from backend.src.youtube_url_checker import check_youtube_video_accessible
    
    # Mock the YouTube object
    mock_yt = MagicMock()
    mock_youtube.return_value = mock_yt
    
    # Set up the property to raise an exception with a specific message
    def raise_age_restricted(*args, **kwargs):
        raise Exception("age restricted")
    
    # Configure mock to raise age restriction error on title access
    type(mock_yt).title = property(lambda self: raise_age_restricted())
    
    # Call the function
    accessible, message = check_youtube_video_accessible("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    
    # Check the result
    assert accessible is False
    assert "age" in message.lower()
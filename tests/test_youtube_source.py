import os
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup mock modules before importing
@pytest.fixture
def setup_module_paths():
    # Create mock modules
    sys.modules['backend.src.base_source'] = MagicMock()
    
    # Define a mock VideoSource class for the base_source module
    class MockVideoSource:
        @staticmethod
        def download_thumbnail(url, output_path):
            # Create a mock file for testing
            with open(output_path, 'w') as f:
                f.write("test content")
            return output_path
            
        @staticmethod
        def generate_content_hash(video_path):
            return "test_hash"
    
    sys.modules['backend.src.base_source'].VideoSource = MockVideoSource
    
    yield
    
    # Clean up
    if 'backend.src.base_source' in sys.modules:
        del sys.modules['backend.src.base_source']


@pytest.fixture
def youtube_source(setup_module_paths):
    """Create a YouTubeSource instance with mocked dependencies"""
    from backend.src.youtube_source import YouTubeSource
    return YouTubeSource()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for outputs"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)


def test_is_valid_url(youtube_source):
    """Test YouTube URL validation"""
    with patch('backend.src.youtube_source.check_youtube_video_accessible') as mock_check:
        # Mock a valid URL
        mock_check.return_value = (True, "Video is accessible")
        
        result = youtube_source.is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        
        assert result is True
        mock_check.assert_called_once_with("https://www.youtube.com/watch?v=dQw4w9WgXcQ")


def test_download_video(youtube_source, temp_dir):
    """Test downloading a video"""
    # Mock YouTube object and its methods
    mock_yt = MagicMock()
    mock_yt.title = "Test Video"
    mock_yt.description = "Test description"
    mock_yt.publish_date.year = 2022
    
    # Mock the stream
    mock_stream = MagicMock()
    mock_stream.download.return_value = os.path.join(temp_dir, "Test Video.mp4")
    
    # Set up the stream filtering chain
    mock_yt.streams.filter.return_value.order_by.return_value.first.return_value = mock_stream
    
    # Mock the thumbnail URL
    mock_yt.thumbnail_url = "https://example.com/thumbnail.jpg"
    
    with patch('backend.src.youtube_source.YouTube', return_value=mock_yt), \
         patch.object(youtube_source, 'download_thumbnail', return_value=os.path.join(temp_dir, "Test Video_thumbnail.jpg")):
        
        # Call the method
        video_path, thumbnail_path, title, description, year = youtube_source.download_video(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ", 
            temp_dir
        )
        
        # Check results
        assert video_path == os.path.join(temp_dir, "Test Video.mp4")
        assert thumbnail_path == os.path.join(temp_dir, "Test Video_thumbnail.jpg")
        assert title == "Test Video"
        assert description == "Test description"
        assert year == 2022


def test_download_video_no_stream(youtube_source, temp_dir):
    """Test handling when no suitable stream is found"""
    # Set up the YouTube mock
    mock_yt = MagicMock()
    mock_yt.title = "Test Video"
    
    # Set up the stream filter to return None
    mock_yt.streams.filter.return_value.order_by.return_value.first.return_value = None
    
    with patch('backend.src.youtube_source.YouTube', return_value=mock_yt):
        # Call the function
        result = youtube_source.download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", temp_dir)
        
        # Check the result
        assert result == (None, None, None, None, None)
        
        # Check that the stream was filtered but no download was attempted
        mock_yt.streams.filter.assert_called_once_with(progressive=True, file_extension='mp4')
        mock_yt.streams.filter.return_value.order_by.assert_called_once_with('resolution')
        mock_yt.streams.filter.return_value.order_by.return_value.first.assert_called_once()


def test_download_video_exception(youtube_source, temp_dir):
    """Test handling exceptions during video download"""
    # Set up the YouTube mock to raise an exception
    with patch('backend.src.youtube_source.YouTube', side_effect=Exception("Network error")):
        # Call the function
        result = youtube_source.download_video("https://www.youtube.com/watch?v=dQw4w9WgXcQ", temp_dir)
        
        # Check the result
        assert result == (None, None, None, None, None)


def test_download_thumbnail_success(youtube_source, temp_dir):
    """Test downloading a thumbnail successfully"""
    # Set up the mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.iter_content.return_value = [b"test data"]
    
    with patch('requests.get', return_value=mock_response):
        # Set up the output path
        thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
        
        # Call the function
        result = youtube_source.download_thumbnail("https://example.com/thumbnail.jpg", thumbnail_path)
        
        # Check the result
        assert result == thumbnail_path
        
        # Check that requests.get was called
        # Uncomment when using real requests mock
        # requests.get.assert_called_once_with("https://example.com/thumbnail.jpg", stream=True)


def test_download_thumbnail_failure(youtube_source, temp_dir):
    """Test handling failures when downloading a thumbnail"""
    # Set up the mock response with a non-200 status code
    mock_response = MagicMock()
    mock_response.status_code = 404
    
    with patch('requests.get', return_value=mock_response):
        # Set up the output path
        thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
        
        # Call the function
        result = youtube_source.download_thumbnail("https://example.com/thumbnail.jpg", thumbnail_path)
        
        # Check the result
        assert result is None


def test_generate_content_hash(youtube_source, temp_dir):
    """Test generating a content hash from a video file"""
    # Create a test file
    test_file_path = os.path.join(temp_dir, "test_video.mp4")
    with open(test_file_path, 'wb') as f:
        f.write(b"This is some test video content")
    
    # Call the function
    hash_value = youtube_source.generate_content_hash(test_file_path)
    
    # Check the result
    assert hash_value is not None
    assert len(hash_value) == 32  # MD5 hash is 32 characters
    
    # Generate the hash again to ensure consistency
    hash_value2 = youtube_source.generate_content_hash(test_file_path)
    assert hash_value == hash_value2
    
    # Create a different file
    diff_file_path = os.path.join(temp_dir, "different_video.mp4")
    with open(diff_file_path, 'wb') as f:
        f.write(b"This is different test video content")
    
    # Generate hash for the different file
    diff_hash = youtube_source.generate_content_hash(diff_file_path)
    assert diff_hash != hash_value
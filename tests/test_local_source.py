import os
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil
from backend.src.local_source import LocalFileSource

# Fix module imports by adjusting path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Setup mocks for imports
class MockVideoSource:
    @staticmethod
    def download_thumbnail(url, output_path):
        return output_path
            
    @staticmethod
    def generate_content_hash(video_path):
        return "test_hash"

# Create mock modules before importing
with patch.dict(sys.modules, {
    'backend.src.base_source': MagicMock(),
    'moviepy.video.io.VideoFileClip': MagicMock(),
    'backend.src.base_source.VideoSource': MockVideoSource
}):
    sys.modules['backend.src.base_source'].VideoSource = MockVideoSource
    from backend.src.local_source import LocalFileSource


@pytest.fixture
def local_source():
    """Create a LocalFileSource instance for testing"""
    return LocalFileSource()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for outputs"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_video_file(temp_dir):
    """Create a sample video file for testing"""
    video_path = os.path.join(temp_dir, "test_video.mp4")
    with open(video_path, 'wb') as f:
        f.write(b"This is a fake MP4 file for testing")
    return video_path


@pytest.fixture
def sample_video_with_description(temp_dir):
    """Create a sample video file with description text file"""
    video_path = os.path.join(temp_dir, "test_video_with_desc.mp4")
    desc_path = os.path.join(temp_dir, "test_video_with_desc.txt")
    
    # Create the video file
    with open(video_path, 'wb') as f:
        f.write(b"This is a fake MP4 file with description")
    
    # Create the description file
    with open(desc_path, 'w') as f:
        f.write("Test Video Title\n")
        f.write("Year: 2023\n")
        f.write("This is a test description.\n")
        f.write("It has multiple lines.\n")
    
    return video_path


def test_is_valid_url_valid_files(local_source, sample_video_file):
    """Test validation of valid local video files"""
    # Test with .mp4 file
    assert local_source.is_valid_url(sample_video_file) is True
    
    # Test with file:// prefix
    file_url = f"file://{sample_video_file}"
    assert local_source.is_valid_url(file_url) is True


def test_is_valid_url_invalid_files(local_source, temp_dir):
    """Test validation of invalid local video files"""
    # Test with non-existent file
    non_existent = os.path.join(temp_dir, "non_existent.mp4")
    assert local_source.is_valid_url(non_existent) is False
    
    # Test with non-video file
    text_file = os.path.join(temp_dir, "text_file.txt")
    with open(text_file, 'w') as f:
        f.write("This is not a video file")
    assert local_source.is_valid_url(text_file) is False


@patch("backend.src.local_source.VideoSource", autospec=True)
def test_download_video_basic(mock_video_source, local_source, sample_video_file, temp_dir):
    """Test basic processing of a local video file"""
    # Mock VideoFileClip
    with patch("backend.src.local_source.VideoFileClip") as mock_video_file_clip:
        mock_clip = MagicMock()
        mock_clip.duration = 60.0
        mock_video_file_clip.return_value = mock_clip
        
        # Create output directory
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Call the function
        video_path, thumbnail_path, title, description, upload_year = local_source.download_video(
            sample_video_file, output_dir
        )
        
        # Check the results
        assert video_path is not None
        assert os.path.exists(video_path)
        assert "test_video.mp4" in video_path
        
        # Check that the title was derived from the filename
        assert title == "test_video"
        
        # Check that a thumbnail was created
        assert thumbnail_path is not None
        assert os.path.exists(thumbnail_path)
        
        # Check that the clip was accessed
        mock_video_file_clip.assert_called_once_with(sample_video_file)
        
        # Check that save_frame was called
        mock_clip.save_frame.assert_called_once()
        mock_clip.close.assert_called_once()


@patch("backend.src.local_source.VideoFileClip")
def test_download_video_with_description(mock_video_file_clip, local_source, sample_video_with_description, temp_dir):
    """Test processing a video with an accompanying description file"""
    # Mock VideoFileClip
    mock_clip = MagicMock()
    mock_clip.duration = 60.0
    mock_video_file_clip.return_value = mock_clip
    
    # Create output directory
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Call the function
    video_path, thumbnail_path, title, description, upload_year = local_source.download_video(
        sample_video_with_description, output_dir
    )
    
    # Check the results
    assert video_path is not None
    assert os.path.exists(video_path)
    
    # Check that metadata was extracted from the description file
    assert title == "Test Video Title"
    assert "This is a test description" in description
    assert "It has multiple lines" in description
    assert upload_year == 2023
    
    # Check that a thumbnail was created
    assert thumbnail_path is not None
    assert os.path.exists(thumbnail_path)


@patch("backend.src.local_source.VideoFileClip")
def test_download_video_non_existent(mock_video_file_clip, local_source, temp_dir):
    """Test handling a non-existent video file"""
    # Create a path to a non-existent video
    non_existent = os.path.join(temp_dir, "non_existent.mp4")
    
    # Call the function
    result = local_source.download_video(non_existent, temp_dir)
    
    # Check the result
    assert result == (None, None, None, None, None)
    
    # Check that VideoFileClip was not called
    mock_video_file_clip.assert_not_called()


@patch("backend.src.local_source.VideoFileClip")
def test_download_video_thumbnail_error(mock_video_file_clip, local_source, sample_video_file, temp_dir):
    """Test handling errors during thumbnail creation"""
    # Mock VideoFileClip to raise an exception during save_frame
    mock_clip = MagicMock()
    mock_clip.duration = 60.0
    mock_clip.save_frame.side_effect = Exception("Error creating thumbnail")
    mock_video_file_clip.return_value = mock_clip
    
    # Create output directory
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Call the function
    video_path, thumbnail_path, title, description, upload_year = local_source.download_video(
        sample_video_file, output_dir
    )
    
    # Check the results
    assert video_path is not None  # Video should still be processed
    assert thumbnail_path is None  # Thumbnail creation failed
    assert title == "test_video"   # Title should still be derived
    
    # Check that save_frame was attempted
    mock_clip.save_frame.assert_called_once()
    mock_clip.close.assert_called_once()


def test_download_video_symlink_if_available(local_source, sample_video_file, temp_dir):
    """Test that symlink is used if available"""
    # Create output directory
    output_dir = os.path.join(temp_dir, "output")
    os.makedirs(output_dir, exist_ok=True)
    
    # Only run the symlink test if the platform supports it
    if hasattr(os, 'symlink'):
        with patch("backend.src.local_source.VideoFileClip") as mock_video_file_clip:
            # Mock VideoFileClip
            mock_clip = MagicMock()
            mock_clip.duration = 60.0
            mock_video_file_clip.return_value = mock_clip
            
            # Call the function
            video_path, _, _, _, _ = local_source.download_video(sample_video_file, output_dir)
            
            # Check if the result is a symlink
            assert os.path.islink(video_path)
            
            # Check that the symlink points to the original file
            assert os.path.samefile(os.path.realpath(video_path), os.path.abspath(sample_video_file))
    else:
        pytest.skip("Symlink not supported on this platform")

import os
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
import shutil

# Fix module imports by adjusting path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Create a proper mock for VideoSource before importing LocalFileSource
class MockVideoSource:
    @staticmethod
    def download_thumbnail(url, output_path):
        return output_path
            
    @staticmethod
    def generate_content_hash(video_path):
        return "test_hash"

# Setup mocks for imports
@pytest.fixture
def mock_dependencies():
    """Setup mock dependencies for LocalFileSource"""
    # Create mock modules before importing
    with patch.dict(sys.modules, {
        'backend.src.base_source': MagicMock(),
        'moviepy.video.io.VideoFileClip': MagicMock(),
    }):
        # Assign our MockVideoSource to the import path
        sys.modules['backend.src.base_source'].VideoSource = MockVideoSource
        
        # Now we can import LocalFileSource
        from backend.src.local_source import LocalFileSource
        
        yield LocalFileSource


@pytest.fixture
def local_source(mock_dependencies):
    """Create a LocalFileSource instance for testing"""
    return mock_dependencies()


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


def test_download_video_with_description(local_source, sample_video_with_description, temp_dir):
    """Test processing a video with an accompanying description file"""
    # Fix: Properly mock VideoFileClip and its methods
    mock_clip = MagicMock()
    mock_clip.duration = 60.0
    
    with patch("backend.src.local_source.VideoFileClip", return_value=mock_clip) as mock_video_file_clip, \
         patch("os.path.exists", side_effect=lambda path: path.endswith('.mp4') or path.endswith('.txt')), \
         patch("os.symlink"), \
         patch("os.path.samefile", return_value=False), \
         patch("os.path.abspath", return_value=sample_video_with_description):
        
        # Create output directory
        output_dir = os.path.join(temp_dir, "output")
        os.makedirs(output_dir, exist_ok=True)
        
        # Call the function
        video_path, thumbnail_path, title, description, upload_year = local_source.download_video(
            sample_video_with_description, output_dir
        )
        
        # Check the results
        assert video_path is not None
        assert title == "Test Video Title"
        assert "This is a test description" in description
        assert upload_year == 2023


def test_download_video_non_existent(local_source, temp_dir):
    """Test handling a non-existent video file"""
    # Create a path to a non-existent video
    non_existent = os.path.join(temp_dir, "non_existent.mp4")
    
    # Call the function
    result = local_source.download_video(non_existent, temp_dir)
    
    # Check the result
    assert result == (None, None, None, None, None)

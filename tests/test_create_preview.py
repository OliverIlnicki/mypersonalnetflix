import os
import pytest
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, call

@pytest.fixture
def temp_dir():
    """Create a temporary directory for outputs"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Clean up
    import shutil
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_video_path():
    """Get the path to a test video in the testdata directory"""
    # Use a placeholder path for testing
    return "/test/sample/video.mp4"

@pytest.fixture
def preview_creator():
    """Create a VideoPreviewCreator instance"""
    # Import here to ensure all mocks can be set up before
    from backend.src.create_preview import VideoPreviewCreator
    return VideoPreviewCreator()

# Fix: Use proper mock path for backend module imports
@patch("backend.src.create_preview.VideoPreviewCreator._get_clip_timing_moviepy")
@patch("backend.src.create_preview.subprocess.run")
def test_create_gif_preview_with_ffmpeg(mock_subprocess_run, mock_get_timing, preview_creator, temp_dir, sample_video_path):
    """Test creating a GIF preview using ffmpeg"""
    # Mock the timing function to return a fixed start time and duration
    mock_get_timing.return_value = (1.0, 5.0)
    
    # Mock the subprocess.run to return success
    mock_palette_result = MagicMock()
    mock_palette_result.returncode = 0
    
    mock_gif_result = MagicMock()
    mock_gif_result.returncode = 0
    
    mock_subprocess_run.side_effect = [mock_palette_result, mock_gif_result]
    
    # Fix: Mock os.path.exists to return True for the video file
    with patch("os.path.exists", return_value=True):
        # Call the function
        result = preview_creator.create_gif_preview(sample_video_path, temp_dir, duration=5)
    
        # Check the result
        assert result is not None
        assert result.endswith(".gif")
        assert os.path.dirname(result) == temp_dir
        
        # Get the actual command used
        palette_call = mock_subprocess_run.call_args_list[0][0][0]
        
        # Just check that ffmpeg and palettegen were called, not exactly how
        assert "ffmpeg" in palette_call[0]
        assert any("palettegen" in arg for arg in palette_call if isinstance(arg, str))

# Fix: Use proper mock path for backend module imports
@patch("backend.src.create_preview.VideoPreviewCreator._get_clip_timing_moviepy")
@patch("backend.src.create_preview.subprocess.run")
@patch("backend.src.create_preview.VideoPreviewCreator._create_gif_preview_moviepy")
def test_create_gif_preview_ffmpeg_failure_fallback(mock_fallback, mock_subprocess_run, mock_get_timing, preview_creator, temp_dir, sample_video_path):    
    """Test fallback to moviepy when ffmpeg fails"""
    # Mock the timing function to return a fixed start time and duration
    mock_get_timing.return_value = (1.0, 5.0)
    
    # Mock the subprocess.run to return failure
    mock_palette_result = MagicMock()
    mock_palette_result.returncode = 1
    mock_palette_result.stderr = b"ffmpeg error"
    
    mock_subprocess_run.return_value = mock_palette_result
    
    # Mock the fallback function
    fallback_path = os.path.join(temp_dir, "fallback.gif")
    mock_fallback.return_value = fallback_path
    
    # Fix: Mock os.path.exists to return True for the video file
    with patch("os.path.exists", return_value=True):
        # Call the function
        result = preview_creator.create_gif_preview(sample_video_path, temp_dir, duration=5)
    
        # Check that the fallback was called with correct parameters
        mock_fallback.assert_called_once_with(sample_video_path, temp_dir, 1.0, 5.0)
        
        # Check the result
        assert result == fallback_path

# Fix: Use proper mock path for backend module imports
@patch("backend.src.create_preview.VideoPreviewCreator._get_clip_timing_moviepy")
@patch("backend.src.create_preview.subprocess.run")
@patch("backend.src.create_preview.VideoFileClip")
def test_create_mp4_preview(mock_video_file_clip, mock_subprocess_run, mock_get_timing, preview_creator, temp_dir, sample_video_path):
    """Test creating an MP4 preview"""
    # Mock the timing function to return a fixed start time and duration
    mock_get_timing.return_value = (1.0, 5.0)
    
    # Mock subprocess.run to fail so we fall back to moviepy
    mock_subprocess_result = MagicMock()
    mock_subprocess_result.returncode = 1
    mock_subprocess_run.return_value = mock_subprocess_result
    
    # Mock VideoFileClip and its methods
    mock_clip = MagicMock()
    mock_subclip = MagicMock()
    mock_resized_clip = MagicMock()
    mock_final_clip = MagicMock()
    
    mock_clip.subclip.return_value = mock_subclip
    mock_subclip.resize.return_value = mock_resized_clip
    mock_resized_clip.without_audio.return_value = mock_final_clip
    
    mock_video_file_clip.return_value = mock_clip
    
    # Fix: Mock os.path.exists to return True for the video file
    with patch("os.path.exists", return_value=True):
        # Call the function
        result = preview_creator.create_mp4_preview(sample_video_path, temp_dir, duration=5)
    
        # Check the result
        assert result is not None
        assert result.endswith("_preview.mp4")
        
        # Check that the video file clip was created
        mock_video_file_clip.assert_called_once_with(sample_video_path)
        
        # Check that subclip was called with correct parameters
        mock_clip.subclip.assert_called_once_with(1.0, 6.0)
        
        # Check that resize was called
        mock_subclip.resize.assert_called_once_with(width=320)
        
        # Check that audio was removed
        mock_resized_clip.without_audio.assert_called_once()
        
        # Check that all clips were closed
        mock_final_clip.close.assert_called_once()
        mock_resized_clip.close.assert_called_once()
        mock_subclip.close.assert_called_once()
        mock_clip.close.assert_called_once()

@patch("backend.src.create_preview.VideoFileClip")
def test_get_clip_timing_moviepy(mock_video_file_clip, preview_creator, sample_video_path):
    """Test getting clip timing from a video"""
    # Mock VideoFileClip
    mock_clip = MagicMock()
    mock_clip.duration = 60.0
    mock_video_file_clip.return_value = mock_clip
    
    # Call the function for a short target duration
    start_time, actual_duration = preview_creator._get_clip_timing_moviepy(sample_video_path, 10)
    
    # Check the results
    assert 12.0 <= start_time <= 48.0  # Should be in the middle 60% of the video
    assert actual_duration == 10.0
    
    # Check that the clip was created and closed
    mock_video_file_clip.assert_called_once_with(sample_video_path)
    mock_clip.close.assert_called_once()

@patch("backend.src.create_preview.VideoFileClip")
def test_get_clip_timing_moviepy_short_video(mock_video_file_clip, preview_creator, sample_video_path):
    """Test getting clip timing from a video shorter than target duration"""
    # Mock VideoFileClip with a short duration
    mock_clip = MagicMock()
    mock_clip.duration = 5.0  # Shorter than typical target duration
    mock_video_file_clip.return_value = mock_clip
    
    # Call the function with a longer target duration
    start_time, actual_duration = preview_creator._get_clip_timing_moviepy(sample_video_path, 10)
    
    # Check the results
    assert start_time == 0.0
    assert actual_duration == 5.0
    
    # Check that the clip was created and closed
    mock_video_file_clip.assert_called_once_with(sample_video_path)
    mock_clip.close.assert_called_once()

@patch("backend.src.create_preview.subprocess.run")
@patch("backend.src.create_preview.VideoFileClip")
def test_extract_thumbnail_ffmpeg(mock_video_file_clip, mock_subprocess_run, preview_creator, temp_dir, sample_video_path):
    """Test extracting a thumbnail using ffmpeg"""
    # Mock the subprocess.run calls
    mock_duration_result = MagicMock()
    mock_duration_result.returncode = 0
    mock_duration_result.stdout = "60.0\n"
    
    mock_thumb_result = MagicMock()
    mock_thumb_result.returncode = 0
    
    mock_subprocess_run.side_effect = [mock_duration_result, mock_thumb_result]
    
    # Set up the output path
    output_path = os.path.join(temp_dir, "thumbnail.jpg")
    
    # Call the function
    result = preview_creator.extract_thumbnail(sample_video_path, output_path)
    
    # Check the result
    assert result is True
    
    # Check the calls to subprocess.run
    assert mock_subprocess_run.call_count == 2
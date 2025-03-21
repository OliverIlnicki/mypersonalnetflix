import unittest
from unittest.mock import patch, MagicMock, Mock
import os
import sys
import shutil
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the function directly
from src.create_gif_preview import create_gif_preview  # Adjust import path as needed

class TestGifPreview(unittest.TestCase):
    def setUp(self):
        self.test_data_dir = os.path.expanduser("~/mypersonalnetflix/data/testdata")
        self.test_output_dir = "/tmp/test_gif_output"
        
        # Ensure test output directory exists
        os.makedirs(self.test_output_dir, exist_ok=True)
        
    def tearDown(self):
        # Clean up any test files created
        if os.path.exists(self.test_output_dir):
            for file in os.listdir(self.test_output_dir):
                file_path = os.path.join(self.test_output_dir, file)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
    
    # Create a mock class to provide as 'self' parameter to the function
    def create_mock_self(self):
        mock_self = MagicMock()
        mock_self.gif_dir = self.test_output_dir
        return mock_self
    
    @patch('os.path.exists', return_value=True)
    @patch('src.create_gif_preview.VideoFileClip')
    def test_create_gif_preview_success(self, mock_video_file_clip, mock_exists):
        # Test with a valid video file
        video_path = os.path.join(self.test_data_dir, "earth.mp4")
        mock_self = self.create_mock_self()
        
        # Configure the mock to create a complete chain
        mock_clip = MagicMock()
        mock_subclip = MagicMock()
        mock_resized = MagicMock()
        
        mock_clip.subclip.return_value = mock_subclip
        mock_subclip.resize.return_value = mock_resized
        mock_video_file_clip.return_value = mock_clip
        
        # Set a known duration
        mock_clip.duration = 60
        
        # Set a return path for write_gif
        expected_gif_path = os.path.join(self.test_output_dir, "earth.gif")
        mock_resized.write_gif.return_value = expected_gif_path
        
        # Mock the random.uniform to return a predictable value
        with patch('random.uniform', return_value=15):
            # Call the function with the mock_self
            gif_path = create_gif_preview(mock_self, video_path)
        
            # Assert expectations
            self.assertIsNotNone(gif_path)
            self.assertEqual(gif_path, expected_gif_path)
            
            # Verify that the methods were called with correct arguments
            mock_clip.subclip.assert_called_once()
            mock_subclip.resize.assert_called_once_with(width=320)
            mock_resized.write_gif.assert_called_once()
            mock_clip.close.assert_called_once()
            # Note: The original function only closes the main clip and not the subclip
    
    @patch('os.path.exists', return_value=True)
    @patch('src.create_gif_preview.VideoFileClip')
    def test_create_gif_preview_short_video(self, mock_video_file_clip, mock_exists):
        # Mock a video shorter than the requested duration
        video_path = os.path.join(self.test_data_dir, "earth.mp4")
        mock_self = self.create_mock_self()
        
        # Configure the mock to create a complete chain
        mock_clip = MagicMock()
        mock_subclip = MagicMock()
        mock_resized = MagicMock()
        
        mock_clip.subclip.return_value = mock_subclip
        mock_subclip.resize.return_value = mock_resized
        mock_video_file_clip.return_value = mock_clip
        
        # Set a short duration
        mock_clip.duration = 10  # 10 seconds, shorter than default 30
        
        # Call with default duration (30 seconds)
        gif_path = create_gif_preview(mock_self, video_path)
        
        # Verify the subclip was created with correct parameters
        # For short videos, it should use the whole video (start=0)
        mock_clip.subclip.assert_called_once_with(0, 10)
        
        # Verify resize was called
        mock_subclip.resize.assert_called_once_with(width=320)
        
        # Verify write_gif was called
        mock_resized.write_gif.assert_called_once()
    
    @patch('os.path.exists', return_value=True)
    @patch('src.create_gif_preview.VideoFileClip')
    def test_create_gif_preview_long_video(self, mock_video_file_clip, mock_exists):
        # Mock a video longer than the requested duration
        video_path = os.path.join(self.test_data_dir, "earth.mp4")
        mock_self = self.create_mock_self()
        
        # Configure the mock to create a complete chain
        mock_clip = MagicMock()
        mock_subclip = MagicMock()
        mock_resized = MagicMock()
        
        mock_clip.subclip.return_value = mock_subclip
        mock_subclip.resize.return_value = mock_resized
        mock_video_file_clip.return_value = mock_clip
        
        # Set a long duration with valid range for random selection
        mock_clip.duration = 100  # 100 seconds, longer than default 30
        
        # With duration=100:
        # start_threshold = 100 * 0.2 = 20
        # end_threshold = 100 * 0.8 = 80
        # max_start = min(80-30, 100-30) = min(50, 70) = 50
        # min_start = max(20, 0) = 20
        # max_start (50) > min_start (20), so start_time is random between them
        
        # Set a fixed random value for consistent testing
        with patch('random.uniform', return_value=35):
            # Call with default duration (30 seconds)
            gif_path = create_gif_preview(mock_self, video_path)
            
            # Verify the subclip was created with correct parameters
            # It should use the random start point (mocked to 35) and duration of 30 seconds
            mock_clip.subclip.assert_called_once_with(35, 65)  # 35 + 30 = 65
    
    @patch('os.path.exists', return_value=True)
    @patch('src.create_gif_preview.VideoFileClip')
    def test_create_gif_preview_custom_duration(self, mock_video_file_clip, mock_exists):
        # Test with a custom duration
        video_path = os.path.join(self.test_data_dir, "earth.mp4")
        mock_self = self.create_mock_self()
        
        # Configure the mock to create a complete chain
        mock_clip = MagicMock()
        mock_subclip = MagicMock()
        mock_resized = MagicMock()
        
        mock_clip.subclip.return_value = mock_subclip
        mock_subclip.resize.return_value = mock_resized
        mock_video_file_clip.return_value = mock_clip
        
        # Set a long duration
        mock_clip.duration = 100  # 100 seconds
        
        # With duration=100 and requested duration=15:
        # start_threshold = 100 * 0.2 = 20
        # end_threshold = 100 * 0.8 = 80
        # max_start = min(80-15, 100-15) = min(65, 85) = 65
        # min_start = max(20, 0) = 20
        # max_start (65) > min_start (20), so start_time is random between them
        
        # Set a fixed random value for consistent testing
        with patch('random.uniform', return_value=40):
            # Call with custom duration (15 seconds)
            gif_path = create_gif_preview(mock_self, video_path, duration=15)
            
            # Verify the subclip was created with correct parameters
            mock_clip.subclip.assert_called_once_with(40, 55)  # 40 + 15 = 55
    
    @patch('os.path.exists', return_value=False)
    def test_create_gif_preview_nonexistent_file(self, mock_exists):
        # Test with a non-existent file
        video_path = os.path.join(self.test_data_dir, "nonexistent.mp4")
        mock_self = self.create_mock_self()
        
        # Call the method
        gif_path = create_gif_preview(mock_self, video_path)
        
        # Assert expectations
        self.assertIsNone(gif_path)
    
    @patch('os.path.exists', return_value=True)
    @patch('src.create_gif_preview.VideoFileClip', side_effect=Exception("Processing error"))
    def test_create_gif_preview_error_during_processing(self, mock_video_file_clip, mock_exists):
        # Test with an error during video processing
        video_path = os.path.join(self.test_data_dir, "earth.mp4")
        mock_self = self.create_mock_self()
        
        # Call the method
        gif_path = create_gif_preview(mock_self, video_path)
        
        # Assert expectations
        self.assertIsNone(gif_path)
    
    @patch('os.path.exists', return_value=True)
    @patch('src.create_gif_preview.VideoFileClip')
    def test_create_gif_preview_boundary_conditions(self, mock_video_file_clip, mock_exists):
        # Test boundary conditions for video durations
        video_path = os.path.join(self.test_data_dir, "earth.mp4")
        mock_self = self.create_mock_self()
        
        # Case 1: Video duration exactly equals requested duration
        # Configure the mock
        mock_clip = MagicMock()
        mock_subclip = MagicMock()
        mock_resized = MagicMock()
        
        mock_clip.subclip.return_value = mock_subclip
        mock_subclip.resize.return_value = mock_resized
        mock_video_file_clip.return_value = mock_clip
        
        mock_clip.duration = 30  # 30 seconds, exactly the default duration
        
        # Call with default duration (30 seconds)
        gif_path = create_gif_preview(mock_self, video_path)
        
        # For videos with duration = requested duration, it should use the whole video
        mock_clip.subclip.assert_called_once_with(0, 30)
        
        # Reset mocks for second case
        mock_video_file_clip.reset_mock()
        
        # Case 2: Video duration where the thresholds don't allow random selection
        # Configure new mocks
        mock_clip2 = MagicMock()
        mock_subclip2 = MagicMock()
        mock_resized2 = MagicMock()
        
        mock_clip2.subclip.return_value = mock_subclip2
        mock_subclip2.resize.return_value = mock_resized2
        mock_video_file_clip.return_value = mock_clip2
        
        mock_clip2.duration = 40  # 40 seconds
        
        # For a 40s video with 30s clip request:
        # start_threshold = 40 * 0.2 = 8
        # end_threshold = 40 * 0.8 = 32
        # max_start = min(32 - 30, 40 - 30) = min(2, 10) = 2
        # min_start = max(8, 0) = 8
        # Since max_start (2) <= min_start (8), start_time should be 0
        
        gif_path = create_gif_preview(mock_self, video_path)
        # With the given constraints, we expect the algorithm to use start=0
        # since there isn't a valid range for random selection
        mock_clip2.subclip.assert_called_once_with(0, 30)  # start from 0, use the requested duration

if __name__ == '__main__':
    unittest.main()
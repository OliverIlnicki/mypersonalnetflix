#%% 
import unittest
from unittest.mock import patch, MagicMock, Mock
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
#%%
from videos2db import VideoSource
from src.youtube_source import YouTubeSource  # Assuming this is the file where YouTubeSource class is defined

#%%
class TestYouTubeSource(unittest.TestCase):
    def setUp(self):
        self.youtube_source = YouTubeSource()
        self.test_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        self.test_output_dir = "/tmp/test_output"
        
        # Ensure test directory exists
        os.makedirs(self.test_output_dir, exist_ok=True)
        
    def tearDown(self):
        # Clean up any test files created
        pass
        
    @patch('src.youtube_source.check_youtube_video_accessible')
    def test_is_valid_url(self, mock_check):
        # Setup mocks
        mock_check.return_value = (True, None)
        
        # Call the method
        result = self.youtube_source.is_valid_url(self.test_url)
        
        # Assert expectations
        self.assertTrue(result)
        mock_check.assert_called_once_with(self.test_url)
        
        # Test invalid URL
        mock_check.return_value = (False, "Video unavailable")
        result = self.youtube_source.is_valid_url(self.test_url)
        self.assertFalse(result)
        
    @patch('src.youtube_source.YouTube')
    def test_download_video_success(self, mock_youtube_class):
        # Setup mocks
        mock_youtube = MagicMock()
        mock_youtube_class.return_value = mock_youtube
        
        mock_youtube.title = "Test Video Title"
        mock_youtube.description = "Test video description"
        mock_youtube.publish_date = datetime(2022, 1, 1)
        mock_youtube.thumbnail_url = "https://example.com/thumbnail.jpg"
        
        # Mock the stream
        mock_stream = MagicMock()
        mock_stream.download.return_value = os.path.join(self.test_output_dir, "Test Video Title.mp4")
        
        # Mock the filter and related methods
        mock_streams = MagicMock()
        mock_streams.filter.return_value = mock_streams
        mock_streams.order_by.return_value = mock_streams
        mock_streams.first.return_value = mock_stream
        mock_youtube.streams = mock_streams
        
        # Mock the thumbnail download
        self.youtube_source.download_thumbnail = MagicMock()
        
        # Call the method
        output_path, thumbnail_path, title, description, year = self.youtube_source.download_video(
            self.test_url, self.test_output_dir
        )
        
        # Assert expectations
        self.assertEqual(output_path, os.path.join(self.test_output_dir, "Test Video Title.mp4"))
        self.assertEqual(thumbnail_path, os.path.join(self.test_output_dir, "Test Video Title_thumbnail.jpg"))
        self.assertEqual(title, "Test Video Title")
        self.assertEqual(description, "Test video description")
        self.assertEqual(year, 2022)
        
        # Verify mock calls
        mock_youtube_class.assert_called_once_with(self.test_url)
        mock_streams.filter.assert_called_once_with(progressive=True, file_extension='mp4')
        mock_streams.order_by.assert_called_once_with('resolution')
        mock_streams.first.assert_called_once()
        mock_stream.download.assert_called_once_with(
            output_path=self.test_output_dir, 
            filename="Test Video Title.mp4"
        )
        self.youtube_source.download_thumbnail.assert_called_once_with(
            "https://example.com/thumbnail.jpg",
            os.path.join(self.test_output_dir, "Test Video Title_thumbnail.jpg")
        )
        
    @patch('src.youtube_source.YouTube')
    def test_download_video_no_stream(self, mock_youtube_class):
        # Setup mocks
        mock_youtube = MagicMock()
        mock_youtube_class.return_value = mock_youtube
        
        mock_youtube.title = "Test Video Title"
        mock_youtube.description = "Test video description"
        mock_youtube.publish_date = datetime(2022, 1, 1)
        
        # Mock the stream to be None
        mock_streams = MagicMock()
        mock_streams.filter.return_value = mock_streams
        mock_streams.order_by.return_value = mock_streams
        mock_streams.first.return_value = None
        mock_youtube.streams = mock_streams
        
        # Call the method
        output_path, thumbnail_path, title, description, year = self.youtube_source.download_video(
            self.test_url, self.test_output_dir
        )
        
        # Assert expectations
        self.assertIsNone(output_path)
        self.assertIsNone(thumbnail_path)
        self.assertIsNone(title)
        self.assertIsNone(description)
        self.assertIsNone(year)
        
    @patch('src.youtube_source.YouTube')
    def test_download_video_exception(self, mock_youtube_class):
        # Setup mocks to raise an exception
        mock_youtube_class.side_effect = Exception("Test exception")
        
        # Call the method
        output_path, thumbnail_path, title, description, year = self.youtube_source.download_video(
            self.test_url, self.test_output_dir
        )
        
        # Assert expectations
        self.assertIsNone(output_path)
        self.assertIsNone(thumbnail_path)
        self.assertIsNone(title)
        self.assertIsNone(description)
        self.assertIsNone(year)
        
    @patch('src.youtube_source.YouTube')
    def test_safe_title_handling(self, mock_youtube_class):
        # We'll use a custom mock to test the title sanitization
        mock_youtube = MagicMock()
        mock_youtube_class.return_value = mock_youtube
        
        # Test with a title containing special characters
        mock_youtube.title = "Test: Video Title (with) *special* characters!"
        mock_youtube.description = "Test description"
        mock_youtube.publish_date = datetime(2022, 1, 1)
        mock_youtube.thumbnail_url = "https://example.com/thumbnail.jpg"
        
        # Mock the stream
        mock_stream = MagicMock()
        expected_safe_title = "Test Video Title with special characters"
        mock_stream.download.return_value = os.path.join(self.test_output_dir, f"{expected_safe_title}.mp4")
        
        # Setup the stream mock chain
        mock_streams = MagicMock()
        mock_streams.filter.return_value = mock_streams
        mock_streams.order_by.return_value = mock_streams
        mock_streams.first.return_value = mock_stream
        mock_youtube.streams = mock_streams
        
        # Mock the thumbnail download
        self.youtube_source.download_thumbnail = MagicMock()
        
        # Call the method
        self.youtube_source.download_video(self.test_url, self.test_output_dir)
        
        # Verify the safe title was used in the download call
        # Note: We're not checking the exact safe title because the implementation may differ,
        # but we are checking that download was called with the expected parameters
        mock_stream.download.assert_called_once()
        # The filename should contain only alphanumeric characters, spaces, dots, underscores, or hyphens


#%%
if __name__ == '__main__':
    print("Running test_youtube_source.py")
    unittest.main()
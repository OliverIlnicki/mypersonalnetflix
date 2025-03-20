"""
Unit tests for YouTube URL Checker.
"""
import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Add the project root directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.youtube_url_checker import check_youtube_video_accessible
from src.youtube_url_checker import check_youtube_video_accessible

class TestYouTubeVideoAccessibility(unittest.TestCase):
    def test_invalid_url(self):
        """Test that a non-YouTube URL is correctly flagged as invalid."""
        invalid_url = "https://example.com/watch?v=invalid"
        accessible, message = check_youtube_video_accessible(invalid_url)
        self.assertFalse(accessible)
        self.assertEqual(message, "Invalid YouTube URL format")
    
    @patch("pytubefix.YouTube")
    @patch("requests.head")
    def test_valid_youtube_url(self, mock_head, mock_YouTube):
        """Test that a valid YouTube URL returns accessible when mocks simulate success."""
        valid_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Setup the mock for requests.head to simulate a 200 OK response.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_head.return_value = mock_response
        
        # Setup the mock for YouTube object.
        yt_instance = MagicMock()
        yt_instance.check_availability.return_value = None
        # Simulate title access for age-check
        yt_instance.title = "Test Video Title"
        mock_YouTube.return_value = yt_instance
        
        accessible, message = check_youtube_video_accessible(valid_url)
        self.assertTrue(accessible)
        self.assertEqual(message, "Video is accessible")

if __name__ == "__main__":
    print("Running test_youtube_url_checker.py")
    unittest.main()
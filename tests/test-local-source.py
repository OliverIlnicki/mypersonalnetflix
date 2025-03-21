#%% 
import unittest
from unittest.mock import patch, MagicMock, Mock
import os
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.local_source import LocalFileSource  # Adjust import path if needed

class TestLocalFileSource(unittest.TestCase):
    def setUp(self):
        self.local_source = LocalFileSource()
        self.test_data_dir = os.path.expanduser("~/mypersonalnetflix/data/testdata")
        self.test_output_dir = "/tmp/test_output"
        
        # Ensure test output directory exists
        os.makedirs(self.test_output_dir, exist_ok=True)
        
    def tearDown(self):
        # Clean up any test files created
        import shutil
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
        
    def test_is_valid_url(self):
        # Test valid MP4 file
        valid_file = os.path.join(self.test_data_dir, "wuerfel.mp4")
        self.assertTrue(self.local_source.is_valid_url(valid_file))
        
        # Test valid MOV file
        valid_mov = os.path.join(self.test_data_dir, "wester_haus.mov")
        self.assertTrue(self.local_source.is_valid_url(valid_mov))
        
        # Test invalid file type
        invalid_file = os.path.join(self.test_data_dir, "sprachtest.wav")
        self.assertFalse(self.local_source.is_valid_url(invalid_file))
        
        # Test file:// protocol
        file_url = f"file://{os.path.join(self.test_data_dir, 'wuerfel.mp4')}"
        self.assertTrue(self.local_source.is_valid_url(file_url))
        
        # Test non-existent file
        non_existent = os.path.join(self.test_data_dir, "nonexistent.mp4")
        self.assertFalse(self.local_source.is_valid_url(non_existent))
    
    @patch('src.local_source.VideoFileClip')
    def test_download_video_with_description(self, mock_video_file_clip):
        # Setup mocks
        mock_clip = MagicMock()
        mock_clip.duration = 100
        mock_video_file_clip.return_value = mock_clip
        
        # Create a mock description file for testing
        wester_haus_path = os.path.join(self.test_data_dir, "wester_haus.mov")
        
        # Call the method
        output_path, thumbnail_path, title, description, year = self.local_source.download_video(
            wester_haus_path, self.test_output_dir
        )
        
        # Assert expectations - title should come from description file's first line
        self.assertIsNotNone(output_path)
        self.assertIsNotNone(thumbnail_path)
        self.assertEqual(title, "Bauernhaus von Wester Solution")
        self.assertEqual(description, "A great product, made for great kids!")
        self.assertEqual(year, 2024)
        
        # Verify mock calls
        mock_video_file_clip.assert_called_once_with(wester_haus_path)
        mock_clip.save_frame.assert_called_once()
        mock_clip.close.assert_called_once()
    
    @patch('src.local_source.VideoFileClip')
    def test_download_video_without_year(self, mock_video_file_clip):
        # Setup mocks
        mock_clip = MagicMock()
        mock_clip.duration = 100
        mock_video_file_clip.return_value = mock_clip
        
        # Path to test file
        wuerfel_path = os.path.join(self.test_data_dir, "wuerfel.mp4")
        
        # Mock file modification time for year fallback
        file_mtime = datetime(2019, 1, 1).timestamp()
        with patch('os.path.getmtime', return_value=file_mtime):
            # Call the method
            output_path, thumbnail_path, title, description, year = self.local_source.download_video(
                wuerfel_path, self.test_output_dir
            )
        
        # Assert expectations - title should come from description even though filename is different
        self.assertIsNotNone(output_path)
        self.assertIsNotNone(thumbnail_path)
        self.assertEqual(title, "Würfelwurf")
        self.assertEqual(description, "Yeah, it's moving ...")
        self.assertEqual(year, 2019)  # Should fall back to file modification time
    
    @patch('src.local_source.VideoFileClip')
    def test_download_video_no_description_file(self, mock_video_file_clip):
        # Setup mocks
        mock_clip = MagicMock()
        mock_clip.duration = 100
        mock_video_file_clip.return_value = mock_clip
        
        # Path to test file without description
        single_dice_path = os.path.join(self.test_data_dir, "single_dice_no_info.mp4")
        
        # Mock file modification time for year
        file_mtime = datetime(2018, 1, 1).timestamp()
        with patch('os.path.getmtime', return_value=file_mtime):
            # Call the method
            output_path, thumbnail_path, title, description, year = self.local_source.download_video(
                single_dice_path, self.test_output_dir
            )
        
        # Assert expectations - should use filename for title since there's no description file
        self.assertIsNotNone(output_path)
        self.assertIsNotNone(thumbnail_path)
        self.assertEqual(title, "single_dice_no_info")  # Should use base filename
        self.assertEqual(description, "")  # Empty description
        self.assertEqual(year, 2018)  # From file mtime
    
    @patch('src.local_source.VideoFileClip')
    def test_corrupt_video_with_thumbnail_error(self, mock_video_file_clip):
        # Setup mocks to raise exception during thumbnail creation
        mock_video_file_clip.side_effect = Exception("Error processing corrupted video")
        
        # Path to corrupt test file
        corrupt_path = os.path.join(self.test_data_dir, "corrupt_video.mp4")
        
        # Call the method
        output_path, thumbnail_path, title, description, year = self.local_source.download_video(
            corrupt_path, self.test_output_dir
        )
        
        # Assert expectations - should still return file info but no thumbnail
        # Title should be from description file, not filename
        self.assertIsNotNone(output_path)
        self.assertIsNone(thumbnail_path)  # Thumbnail creation failed
        self.assertEqual(title, "Corrupt Video")  # From description file
        self.assertEqual(description, "how could you even try to load it. It is not a working file")
    
    def test_wrong_file_format(self):
        # Path to non-video file
        wav_path = os.path.join(self.test_data_dir, "sprachtest.wav")
        
        # Call the method
        output_path, thumbnail_path, title, description, year = self.local_source.download_video(
            wav_path, self.test_output_dir
        )
        
        # Assert expectations - should still process it even though isvalid_url would return false
        # Title should be from description file
        self.assertIsNotNone(output_path)
        self.assertEqual(title, "Würfelwurf")  # From sprachtest.txt description file
        self.assertEqual(description, "Yeah, it's moving ...")
        
    def test_nonexistent_file(self):
        # Path to non-existent file
        nonexistent_path = os.path.join(self.test_data_dir, "nonexistent.mp4")
        
        # Call the method
        output_path, thumbnail_path, title, description, year = self.local_source.download_video(
            nonexistent_path, self.test_output_dir
        )
        
        # Assert expectations
        self.assertIsNone(output_path)
        self.assertIsNone(thumbnail_path)
        self.assertIsNone(title)
        self.assertIsNone(description)
        self.assertIsNone(year)
    
    @patch('os.symlink')
    @patch('src.local_source.VideoFileClip')
    def test_symlink_creation(self, mock_video_file_clip, mock_symlink):
        # Setup mocks
        mock_clip = MagicMock()
        mock_clip.duration = 100
        mock_video_file_clip.return_value = mock_clip
        
        # Test file
        wuerfel_path = os.path.join(self.test_data_dir, "wuerfel.mp4")
        
        # Call the method
        self.local_source.download_video(wuerfel_path, self.test_output_dir)
        
        # Verify symlink was attempted
        mock_symlink.assert_called_once()
    
    @patch('os.symlink')
    @patch('src.local_source.VideoFileClip')
    def test_symlink_fallback_to_copy(self, mock_video_file_clip, mock_symlink):
        # Setup mocks
        mock_clip = MagicMock()
        mock_clip.duration = 100
        mock_video_file_clip.return_value = mock_clip
        
        # Make symlink fail
        mock_symlink.side_effect = Exception("Symlink failed")
        
        # Mock file open and write for copy operation
        m_open = unittest.mock.mock_open()
        with patch('builtins.open', m_open):
            # Test file
            wuerfel_path = os.path.join(self.test_data_dir, "wuerfel.mp4")
            
            # Call the method
            self.local_source.download_video(wuerfel_path, self.test_output_dir)
        
        # Verify symlink was attempted and fallback to copy occurred
        mock_symlink.assert_called_once()
        m_open.assert_called()  # File was opened for copying

#%%
if __name__ == '__main__':
    print("Running test_local_source.py")
    unittest.main()
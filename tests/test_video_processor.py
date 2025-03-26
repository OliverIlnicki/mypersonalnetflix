import os
import sys
import pytest
import tempfile
import json
import shutil
from unittest.mock import MagicMock, patch, mock_open

# Add the processor fixture - this was missing in the original test file
@pytest.fixture
def processor(temp_data_dir, mock_db_helper, mock_preview_creator, mock_youtube_source, mock_local_source):
    """Create a VideoProcessor instance with mocked dependencies"""
    with patch('backend.src.video_processor.DatabaseHelper', return_value=mock_db_helper), \
         patch('backend.src.video_processor.VideoPreviewCreator', return_value=mock_preview_creator), \
         patch('os.makedirs'), \
         patch('os.path.exists', return_value=True), \
         patch('os.rename'), \
         patch('os.remove'), \
         patch('os.path.islink', return_value=False), \
         patch('os.path.relpath', return_value="relative/path"):
        
        # Import here to ensure patches take effect
        from backend.src.video_processor import VideoProcessor
        
        processor = VideoProcessor(temp_data_dir)
        
        # Register our mock sources
        processor.video_sources = {
            "youtube": mock_youtube_source,
            "local": mock_local_source
        }
        
        yield processor

@pytest.fixture
def temp_data_dir():
    """Create a temporary directory for test data"""
    # Create a temporary directory
    temp_dir = tempfile.mkdtemp()
    
    # Yield the path to the temp directory
    yield temp_dir
    
    # Clean up after the test
    shutil.rmtree(temp_dir, ignore_errors=True)

@pytest.fixture
def mock_db_helper():
    """Create a mock DatabaseHelper instance"""
    with patch('backend.src.db_helper.DatabaseHelper', autospec=True) as mock_db:
        # Configure the mock to return a specific is_duplicate response
        instance = mock_db.return_value
        instance.is_duplicate.return_value = False
        yield instance

@pytest.fixture
def mock_preview_creator():
    """Create a mock VideoPreviewCreator instance"""
    with patch('backend.src.create_preview.VideoPreviewCreator', autospec=True) as mock_preview:
        instance = mock_preview.return_value
        # Configure the mock to return paths for preview creation
        instance.create_mp4_preview.return_value = "/tmp/test_preview.mp4"
        instance.create_gif_preview.return_value = "/tmp/test_preview.gif"
        yield instance

@pytest.fixture
def mock_youtube_source():
    """Create a mock YouTubeSource instance"""
    with patch('backend.src.youtube_source.YouTubeSource', autospec=True) as mock_source:
        instance = mock_source.return_value
        # Configure the mock for URL validation and download
        instance.is_valid_url.return_value = True
        instance.download_video.return_value = (
            "/tmp/video.mp4",          # video_path
            "/tmp/thumbnail.jpg",      # thumbnail_path
            "Test Video Title",        # video_title
            "Test video description",  # video_description
            2023                       # upload_year
        )
        instance.generate_content_hash.return_value = "abcdef123456"
        yield instance

@pytest.fixture
def mock_local_source():
    """Create a mock LocalFileSource instance"""
    with patch('backend.src.local_source.LocalFileSource', autospec=True) as mock_source:
        instance = mock_source.return_value
        # Local source only validates local paths
        instance.is_valid_url.side_effect = lambda url: url.startswith(("/", "file://"))
        instance.download_video.return_value = (
            "/tmp/local_video.mp4",     # video_path
            "/tmp/local_thumbnail.jpg", # thumbnail_path
            "Local Test Video",         # video_title
            "Local test description",   # video_description
            2022                        # upload_year
        )
        instance.generate_content_hash.return_value = "localfile789012"
        yield instance

class TestVideoProcessor:
    """Tests for the VideoProcessor class"""
    
    def test_ensure_user_directories(self, processor, temp_data_dir):
        """Test that user directories are created correctly"""
        with patch('os.makedirs') as mock_makedirs, \
             patch('os.path.exists', return_value=False):
            
            result = processor.ensure_user_directories("testuser")
            
            # Verify all expected directories are created
            expected_dirs = {
                "user_dir": os.path.join(temp_data_dir, "testuser"),
                "temp_dir": os.path.join(temp_data_dir, "testuser", "temp_videos"),
                "thumbnails_dir": os.path.join(temp_data_dir, "testuser", "thumbnails"),
                "gif_dir": os.path.join(temp_data_dir, "testuser", "previews")
            }
            
            assert result == expected_dirs
            assert mock_makedirs.call_count >= 4  # At least 4 directories created
    
    def test_process_url_youtube(self, processor, mock_youtube_source, mock_db_helper):
        """Test processing a YouTube URL"""
        youtube_url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        
        # Process a YouTube URL
        result = processor.process_url(youtube_url, "testuser")
        
        # Verify correct source was selected and used
        mock_youtube_source.is_valid_url.assert_called_with(youtube_url)
        assert mock_youtube_source.download_video.called
        
        # Verify processing steps were completed
        assert processor.preview_creator.create_mp4_preview.called
        assert processor.preview_creator.create_gif_preview.called
        assert mock_db_helper.save_to_database.called
        
        # Verify the result contains expected video information
        assert result is not None
        assert result["user"] == "testuser"
        assert result["url"] == youtube_url
        assert result["source"] == "youtube"
        assert result["title"] == "Test Video Title"
        assert result["preview_type"] == "mp4"  # Should prefer MP4 over GIF
    
    def test_process_url_local_file(self, processor, mock_local_source, mock_db_helper, temp_data_dir):
        """Test processing a local file path"""
        # Process a local file path
        local_path = "/data/testdata/earth.mp4"
        
        # Configure YouTube source to reject the local path
        mock_youtube = processor.video_sources["youtube"]
        mock_youtube.is_valid_url.return_value = False
        
        # Process the path
        result = processor.process_url(local_path, "testuser")
        
        # Verify correct source was selected and used
        mock_local_source.is_valid_url.assert_called_with(local_path)
        assert mock_local_source.download_video.called
        mock_local_source.generate_content_hash.assert_called_once()
        
        # Verify processing steps were completed
        assert processor.preview_creator.create_mp4_preview.called
        assert processor.preview_creator.create_gif_preview.called
        assert mock_db_helper.save_to_database.called
        
        # Verify the result contains expected video information
        assert result is not None
        assert result["user"] == "testuser"
        assert result["url"] == local_path
        assert result["source"] == "local"
        assert result["title"] == "Local Test Video"
        assert result["preview_type"] == "mp4"  # Should prefer MP4 over GIF
    
    def test_process_url_duplicate(self, processor, mock_db_helper):
        """Test processing a duplicate video that should be skipped"""
        # Configure mock to indicate a duplicate
        mock_db_helper.is_duplicate.return_value = True
        
        result = processor.process_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "testuser")
        
        # Result should be None for duplicates
        assert result is None
        
        # Verify duplicate check was performed but processing stopped
        assert mock_db_helper.is_duplicate.called
        assert not mock_db_helper.save_to_database.called
    
    def test_process_url_no_username(self, processor):
        """Test that processing fails if no username is provided"""
        result = processor.process_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "")
        
        # Result should be None when username is missing
        assert result is None
    
    def test_process_links_file(self, processor):
        """Test processing a file containing multiple video URLs"""
        links_content = """
        https://www.youtube.com/watch?v=video1
        https://www.youtube.com/watch?v=video2
        https://www.youtube.com/watch?v=video3
        """
        
        with patch('builtins.open', mock_open(read_data=links_content)):
            # Mock the process_url method to track calls
            processor.process_url = MagicMock(side_effect=[
                {"url": "https://www.youtube.com/watch?v=video1", "title": "Video 1"},
                {"url": "https://www.youtube.com/watch?v=video2", "title": "Video 2"},
                {"url": "https://www.youtube.com/watch?v=video3", "title": "Video 3"}
            ])
            
            results = processor.process_links_file("links.txt", "testuser")
            
            # Verify all URLs were processed
            assert len(results) == 3
            assert processor.process_url.call_count == 3
    
    def test_process_local_directory(self, processor):
        """Test processing all video files in a directory"""
        # Mock os.walk to return a list of files
        video_files = [
            "/videos/video1.mp4",
            "/videos/video2.avi",
            "/videos/subdir/video3.mkv"
        ]
        
        with patch('os.path.isdir', return_value=True), \
             patch('os.walk', return_value=[
                 ("/videos", [], ["video1.mp4", "video2.avi", "document.txt"]),
                 ("/videos/subdir", [], ["video3.mkv", "image.jpg"])
             ]):
            
            # Mock the process_url method to track calls
            processor.process_url = MagicMock(side_effect=[
                {"url": "/videos/video1.mp4", "title": "Video 1"},
                {"url": "/videos/video2.avi", "title": "Video 2"},
                {"url": "/videos/subdir/video3.mkv", "title": "Video 3"}
            ])
            
            results = processor.process_local_directory("/videos", "testuser")
            
            # Verify all video files were processed
            assert len(results) == 3
            assert processor.process_url.call_count == 3
    
    def test_save_results(self, processor, temp_data_dir):
        """Test saving results to a JSON file"""
        results = [
            {"title": "Video 1", "url": "http://example.com/1"},
            {"title": "Video 2", "url": "http://example.com/2"}
        ]
        
        with patch('builtins.open', mock_open()) as mock_file, \
             patch('json.dump') as mock_json:
            
            saved_paths = processor.save_results(results, "testuser")
            
            # Verify file was opened and JSON was written
            assert mock_file.called
            assert mock_json.called
            
            # Verify correct path was returned
            expected_path = os.path.join(temp_data_dir, "testuser", "video_data.json")
            assert saved_paths["json_path"] == expected_path
    
    def test_query_database(self, processor, mock_db_helper):
        """Test querying the database with filters"""
        # Configure mock to return specific results
        mock_db_helper.query_database.return_value = [
            {"id": 1, "title": "Video 1", "user": "testuser", "upload_year": 2023},
            {"id": 2, "title": "Video 2", "user": "testuser", "upload_year": 2023}
        ]
        
        results = processor.query_database(user="testuser", year=2023, source="youtube")
        
        # Verify query was passed to database helper
        mock_db_helper.query_database.assert_called_with(
            user="testuser", year=2023, source="youtube"
        )
        
        # Verify results were returned
        assert len(results) == 2
        assert results[0]["title"] == "Video 1"
        assert results[1]["title"] == "Video 2"

    def test_close(self, processor, mock_db_helper):
        """Test closing the database connection"""
        processor.close()
        
        # Verify database helper close was called
        assert mock_db_helper.close.called
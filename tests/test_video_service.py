import os
import pytest
import sqlite3
import tempfile
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Add the backend directory to the path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

# Import the video_service module
from video_service import VideoService


@pytest.fixture
def temp_db():
    """Create a temporary database file for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    # Create a test database with sample data
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    
    # Create videos table
    cursor.execute('''
    CREATE TABLE videos (
        id INTEGER PRIMARY KEY,
        user TEXT,
        url TEXT,
        title TEXT,
        description TEXT,
        thumb_path TEXT,
        vid_preview_path TEXT,
        upload_year INTEGER,
        source TEXT,
        preview_type TEXT
    )
    ''')
    
    # Insert test data
    cursor.execute('''
    INSERT INTO videos (id, user, url, title, description, thumb_path, vid_preview_path, upload_year, source, preview_type)
    VALUES (1, 'TestUser', 'https://youtube.com/watch?v=ABC123', 'Test Video', 'A test video', 
            'TestUser/thumbnails/test.jpg', 'TestUser/previews/test.gif', 2023, 'youtube', 'gif')
    ''')
    
    cursor.execute('''
    INSERT INTO videos (id, user, url, title, description, thumb_path, vid_preview_path, upload_year, source, preview_type)
    VALUES (2, 'TestUser', 'https://youtube.com/watch?v=DEF456', 'Second Video', 'Another test video', 
            'TestUser/thumbnails/second.jpg', 'TestUser/previews/second.mp4', 2022, 'youtube', 'mp4')
    ''')
    
    cursor.execute('''
    INSERT INTO videos (id, user, url, title, description, thumb_path, vid_preview_path, upload_year, source, preview_type)
    VALUES (3, 'OtherUser', 'https://youtube.com/watch?v=GHI789', 'Other Video', 'From another user', 
            'OtherUser/thumbnails/other.jpg', 'OtherUser/previews/other.gif', 2023, 'youtube', 'gif')
    ''')
    
    conn.commit()
    conn.close()
    
    yield path
    
    # Cleanup
    os.unlink(path)


@pytest.fixture
def video_service(temp_db):
    """Create a VideoService instance with the test database"""
    # Create a temp directory to act as the data directory
    temp_dir = tempfile.mkdtemp()
    
    # Move the temporary database to the data directory
    os.rename(temp_db, os.path.join(temp_dir, "videos.db"))
    
    # Create a VideoService instance
    service = VideoService(data_dir=temp_dir)
    
    yield service
    
    # Cleanup
    import shutil
    shutil.rmtree(temp_dir)


def test_get_videos(video_service):
    """Test retrieving all videos from the database"""
    videos = video_service.get_videos()
    
    assert len(videos) == 3
    assert videos[0]["title"] == "Test Video"
    assert videos[1]["title"] == "Second Video"
    assert videos[2]["title"] == "Other Video"


def test_get_videos_with_user_filter(video_service):
    """Test retrieving videos filtered by user"""
    videos = video_service.get_videos(user="TestUser")
    
    assert len(videos) == 2
    assert all(v["user"] == "TestUser" for v in videos)


def test_get_videos_with_year_filter(video_service):
    """Test retrieving videos filtered by year"""
    videos = video_service.get_videos(year=2023)
    
    assert len(videos) == 2
    assert all(v["upload_year"] == 2023 for v in videos)


def test_get_videos_with_search_query(video_service):
    """Test retrieving videos filtered by search query"""
    videos = video_service.get_videos(search_query="Second")
    
    assert len(videos) == 1
    assert videos[0]["title"] == "Second Video"


def test_get_video_by_id(video_service):
    """Test retrieving a specific video by ID"""
    video = video_service.get_video_by_id(1)
    
    assert video is not None
    assert video["id"] == 1
    assert video["title"] == "Test Video"
    assert video["user"] == "TestUser"


def test_get_video_by_id_not_found(video_service):
    """Test retrieving a non-existent video by ID"""
    video = video_service.get_video_by_id(999)
    
    assert video is None


def test_get_users(video_service):
    """Test retrieving all unique users"""
    users = video_service.get_users()
    
    assert len(users) == 2
    assert "TestUser" in users
    assert "OtherUser" in users


def test_get_years(video_service):
    """Test retrieving all unique years"""
    years = video_service.get_years()
    
    assert len(years) == 2
    assert 2022 in years
    assert 2023 in years
    assert years == [2022, 2023]  # Should be sorted


def test_get_random_featured_video(video_service):
    """Test retrieving a random featured video"""
    featured = video_service.get_random_featured_video()
    
    assert featured is not None
    assert "id" in featured
    assert "title" in featured


def test_get_related_videos(video_service):
    """Test retrieving related videos"""
    video = {"id": 1, "user": "TestUser"}
    related = video_service.get_related_videos(video)
    
    assert len(related) == 1
    assert related[0]["id"] == 2
    assert related[0]["user"] == "TestUser"


def test_enhance_video_data(video_service):
    """Test enhancing video data with additional fields"""
    video = {
        "id": 1,
        "title": "Test Video",
        "thumb_path": "TestUser/thumbnails/test.jpg",
        "vid_preview_path": "TestUser/previews/test.gif",
        "url": "https://youtube.com/watch?v=ABC123"
    }
    
    enhanced = video_service.enhance_video_data(video)
    
    assert enhanced["image_url"] == "/data/TestUser/thumbnails/test.jpg"
    assert enhanced["preview_url"] == "/data/TestUser/previews/test.gif"
    assert enhanced["youtube_id"] == "ABC123"
    assert enhanced["preview_type"] == "gif"


def test_extract_youtube_id(video_service):
    """Test extracting YouTube video ID from different URL formats"""
    # Standard YouTube URL
    youtube_id = video_service.extract_youtube_id("https://www.youtube.com/watch?v=ABC123")
    assert youtube_id == "ABC123"
    
    # Short YouTube URL
    youtube_id = video_service.extract_youtube_id("https://youtu.be/DEF456")
    assert youtube_id == "DEF456"
    
    # URL with additional parameters
    youtube_id = video_service.extract_youtube_id("https://www.youtube.com/watch?v=GHI789&t=30s")
    assert youtube_id == "GHI789"
    
    # Non-YouTube URL
    youtube_id = video_service.extract_youtube_id("https://example.com/video")
    assert youtube_id is None
    
    # None input
    youtube_id = video_service.extract_youtube_id(None)
    assert youtube_id is None


def test_get_video_path(video_service):
    """Test converting relative paths to URL paths"""
    path = video_service.get_video_path("TestUser/thumbnails/test.jpg")
    assert path == "/data/TestUser/thumbnails/test.jpg"
    
    # Test with None input
    path = video_service.get_video_path(None)
    assert path is None

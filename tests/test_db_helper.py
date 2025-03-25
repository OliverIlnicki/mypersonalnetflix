import os
import pytest
import sqlite3
import tempfile
import sys
from pathlib import Path
from backend.src.db_helper import DatabaseHelper


@pytest.fixture
def temp_db_path():
    """Create a temporary database file path for testing"""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    
    yield path
    
    # Clean up after the test
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def db_helper(temp_db_path):
    """Create a DatabaseHelper instance with a temporary database"""
    helper = DatabaseHelper(temp_db_path)
    yield helper
    helper.close()


def test_init_database(db_helper, temp_db_path):
    """Test that the database is initialized with the correct schema"""
    # Check that the database file exists
    assert os.path.exists(temp_db_path)
    
    # Connect to the database and check the schema
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    
    # Check that the videos table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='videos'")
    table = cursor.fetchone()
    assert table is not None
    
    # Check that the required columns exist
    cursor.execute("PRAGMA table_info(videos)")
    columns = cursor.fetchall()
    column_names = [col[1] for col in columns]
    
    required_columns = [
        "id", "user", "url", "source", "title", "description", 
        "thumb_path", "vid_preview_path", "upload_year", "content_hash", 
        "preview_type", "date_added"
    ]
    
    for col in required_columns:
        assert col in column_names
    
    # Check that the indexes exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
    indexes = cursor.fetchall()
    index_names = [idx[0] for idx in indexes]
    
    assert "idx_content_hash" in index_names
    assert "idx_user" in index_names
    
    conn.close()


def test_save_to_database(db_helper):
    """Test saving a video record to the database"""
    video_info = {
        "user": "TestUser",
        "url": "https://example.com/video",
        "source": "youtube",
        "title": "Test Video",
        "description": "A test video",
        "thumb_path": "TestUser/thumbnails/test.jpg",
        "vid_preview_path": "TestUser/previews/test.gif",
        "upload_year": 2023,
        "content_hash": "abc123",
        "preview_type": "gif"
    }
    
    # Save the record
    video_id = db_helper.save_to_database(video_info)
    
    # Check that an ID was returned
    assert video_id is not None
    
    # Query the database to check the record
    conn = sqlite3.connect(db_helper.db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
    row = cursor.fetchone()
    
    # Get column names
    columns = [description[0] for description in cursor.description]
    record = dict(zip(columns, row))
    
    conn.close()
    
    # Check the record values
    assert record["user"] == "TestUser"
    assert record["url"] == "https://example.com/video"
    assert record["title"] == "Test Video"
    assert record["preview_type"] == "gif"


def test_is_duplicate_url(db_helper):
    """Test checking for duplicate URLs"""
    # Save a record
    video_info = {
        "user": "TestUser",
        "url": "https://example.com/video1",
        "source": "youtube",
        "title": "Test Video",
        "description": "A test video",
        "thumb_path": "TestUser/thumbnails/test.jpg",
        "vid_preview_path": "TestUser/previews/test.gif",
        "upload_year": 2023,
        "content_hash": "abc123",
        "preview_type": "gif"
    }
    
    db_helper.save_to_database(video_info)
    
    # Check for duplicate URL
    is_dup = db_helper.is_duplicate("https://example.com/video1", "xyz789")
    assert is_dup is True
    
    # Check for non-duplicate URL
    is_dup = db_helper.is_duplicate("https://example.com/different", "xyz789")
    assert is_dup is False


def test_is_duplicate_content_hash(db_helper):
    """Test checking for duplicate content hashes"""
    # Save a record
    video_info = {
        "user": "TestUser",
        "url": "https://example.com/video1",
        "source": "youtube",
        "title": "Test Video",
        "description": "A test video",
        "thumb_path": "TestUser/thumbnails/test.jpg",
        "vid_preview_path": "TestUser/previews/test.gif",
        "upload_year": 2023,
        "content_hash": "abc123",
        "preview_type": "gif"
    }
    
    db_helper.save_to_database(video_info)
    
    # Check for duplicate content hash
    is_dup = db_helper.is_duplicate("https://example.com/different", "abc123")
    assert is_dup is True
    
    # Check for non-duplicate content hash
    is_dup = db_helper.is_duplicate("https://example.com/different", "xyz789")
    assert is_dup is False


def test_query_database(db_helper):
    """Test querying the database with filters"""
    # Save some records
    db_helper.save_to_database({
        "user": "User1",
        "url": "https://example.com/video1",
        "source": "youtube",
        "title": "Video 1",
        "description": "First video",
        "thumb_path": "path/to/thumb1.jpg",
        "vid_preview_path": "path/to/preview1.gif",
        "upload_year": 2021,
        "content_hash": "hash1",
        "preview_type": "gif"
    })
    
    db_helper.save_to_database({
        "user": "User1",
        "url": "https://example.com/video2",
        "source": "youtube",
        "title": "Video 2",
        "description": "Second video",
        "thumb_path": "path/to/thumb2.jpg",
        "vid_preview_path": "path/to/preview2.gif",
        "upload_year": 2022,
        "content_hash": "hash2",
        "preview_type": "gif"
    })
    
    db_helper.save_to_database({
        "user": "User2",
        "url": "https://example.com/video3",
        "source": "local",
        "title": "Video 3",
        "description": "Third video",
        "thumb_path": "path/to/thumb3.jpg",
        "vid_preview_path": "path/to/preview3.mp4",
        "upload_year": 2022,
        "content_hash": "hash3",
        "preview_type": "mp4"
    })
    
    # Query with no filters
    results = db_helper.query_database()
    assert len(results) == 3
    
    # Query by user
    results = db_helper.query_database(user="User1")
    assert len(results) == 2
    assert all(r["user"] == "User1" for r in results)
    
    # Query by year
    results = db_helper.query_database(year=2022)
    assert len(results) == 2
    assert all(r["upload_year"] == 2022 for r in results)
    
    # Query by source
    results = db_helper.query_database(source="local")
    assert len(results) == 1
    assert results[0]["source"] == "local"
    
    # Query with multiple filters
    results = db_helper.query_database(user="User1", year=2022)
    assert len(results) == 1
    assert results[0]["user"] == "User1"
    assert results[0]["upload_year"] == 2022


def test_get_video_by_id(db_helper):
    """Test retrieving a video by ID"""
    # Save a record
    video_id = db_helper.save_to_database({
        "user": "TestUser",
        "url": "https://example.com/testvideo",
        "source": "youtube",
        "title": "Test Video",
        "description": "A test video",
        "thumb_path": "TestUser/thumbnails/test.jpg",
        "vid_preview_path": "TestUser/previews/test.gif",
        "upload_year": 2023,
        "content_hash": "abc123",
        "preview_type": "gif"
    })
    
    # Retrieve the record
    video = db_helper.get_video_by_id(video_id)
    
    # Check that the record was retrieved correctly
    assert video is not None
    assert video["id"] == video_id
    assert video["title"] == "Test Video"
    
    # Test retrieving a non-existent video
    video = db_helper.get_video_by_id(9999)
    assert video is None


def test_get_videos_by_user(db_helper):
    """Test retrieving videos by user"""
    # Save some records
    db_helper.save_to_database({
        "user": "User1",
        "url": "https://example.com/video1",
        "source": "youtube",
        "title": "Video 1",
        "description": "First video",
        "thumb_path": "path/to/thumb1.jpg",
        "vid_preview_path": "path/to/preview1.gif",
        "upload_year": 2021,
        "content_hash": "hash1",
        "preview_type": "gif"
    })
    
    db_helper.save_to_database({
        "user": "User1",
        "url": "https://example.com/video2",
        "source": "youtube",
        "title": "Video 2",
        "description": "Second video",
        "thumb_path": "path/to/thumb2.jpg",
        "vid_preview_path": "path/to/preview2.gif",
        "upload_year": 2022,
        "content_hash": "hash2",
        "preview_type": "gif"
    })
    
    db_helper.save_to_database({
        "user": "User2",
        "url": "https://example.com/video3",
        "source": "local",
        "title": "Video 3",
        "description": "Third video",
        "thumb_path": "path/to/thumb3.jpg",
        "vid_preview_path": "path/to/preview3.mp4",
        "upload_year": 2022,
        "content_hash": "hash3",
        "preview_type": "mp4"
    })
    
    # Get videos for User1
    videos = db_helper.get_videos_by_user("User1")
    assert len(videos) == 2
    assert all(v["user"] == "User1" for v in videos)
    
    # Get videos for User2
    videos = db_helper.get_videos_by_user("User2")
    assert len(videos) == 1
    assert videos[0]["user"] == "User2"
    
    # Get videos for non-existent user
    videos = db_helper.get_videos_by_user("NonExistentUser")
    assert len(videos) == 0


def test_delete_video(db_helper):
    """Test deleting a video from the database"""
    # Save a record
    video_id = db_helper.save_to_database({
        "user": "TestUser",
        "url": "https://example.com/testvideo",
        "source": "youtube",
        "title": "Test Video",
        "description": "A test video",
        "thumb_path": "TestUser/thumbnails/test.jpg",
        "vid_preview_path": "TestUser/previews/test.gif",
        "upload_year": 2023,
        "content_hash": "abc123",
        "preview_type": "gif"
    })
    
    # Check that the record exists
    video = db_helper.get_video_by_id(video_id)
    assert video is not None
    
    # Delete the record
    result = db_helper.delete_video(video_id)
    assert result is True
    
    # Check that the record was deleted
    video = db_helper.get_video_by_id(video_id)
    assert video is None
    
    # Try to delete a non-existent record
    result = db_helper.delete_video(9999)
    assert result is False
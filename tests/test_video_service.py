import os
import pytest
import sqlite3
import tempfile
import shutil
from backend.video_service import VideoService

@pytest.fixture
def temp_db():
    """Erstellt eine temporäre SQLite-Datenbank mit Testdaten."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "videos.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
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
    cursor.executemany('''
        INSERT INTO videos (id, user, url, title, description, thumb_path, vid_preview_path, upload_year, source, preview_type)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', [
        (1, 'TestUser', 'https://youtube.com/watch?v=ABC123', 'Test Video', 'A test video', 'TestUser/thumbnails/test.jpg', 'TestUser/previews/test.gif', 2023, 'youtube', 'gif'),
        (2, 'TestUser', 'https://youtube.com/watch?v=DEF456', 'Second Video', 'Another test video', 'TestUser/thumbnails/second.jpg', 'TestUser/previews/second.mp4', 2022, 'youtube', 'mp4'),
        (3, 'OtherUser', 'https://youtube.com/watch?v=GHI789', 'Other Video', 'From another user', 'OtherUser/thumbnails/other.jpg', 'OtherUser/previews/other.gif', 2023, 'youtube', 'gif')
    ])
    conn.commit()
    conn.close()
    
    yield db_path
    shutil.rmtree(temp_dir)

@pytest.fixture
def video_service(temp_db):
    """Erstellt eine VideoService-Instanz mit einer Testdatenbank."""
    service = VideoService(data_dir=os.path.dirname(temp_db))
    yield service

def test_get_videos(video_service):
    videos = video_service.get_videos()
    assert len(videos) == 3
    assert videos[0]["title"] == "Test Video"
    assert videos[1]["title"] == "Second Video"
    assert videos[2]["title"] == "Other Video"

def test_get_video_by_id(video_service):
    video = video_service.get_video_by_id(1)
    assert video is not None
    assert video["id"] == 1
    assert video["title"] == "Test Video"

def test_get_users(video_service):
    users = video_service.get_users()
    assert set(users) == {"TestUser", "OtherUser"}

def test_get_years(video_service):
    years = video_service.get_years()
    assert years == [2022, 2023]

def test_extract_youtube_id(video_service):
    assert video_service.extract_youtube_id("https://www.youtube.com/watch?v=ABC123") == "ABC123"
    assert video_service.extract_youtube_id("https://youtu.be/DEF456") == "DEF456"
    assert video_service.extract_youtube_id(None) is None

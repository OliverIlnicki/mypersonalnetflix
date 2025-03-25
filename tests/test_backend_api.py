import os
import pytest
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path
from fastapi.testclient import TestClient
from backend.backend_api import app, video_service


@pytest.fixture
def client():
    """Test client for FastAPI application"""
    return TestClient(app)


@pytest.fixture
def mock_video_service():
    """Mock the VideoService class"""
    with patch("backend.backend_api.video_service") as mock_service:
        yield mock_service

def test_get_videos(client, mock_video_service):
    """Test the /api/videos endpoint"""
    # Setup mock return value
    mock_video_service.get_videos.return_value = [
        {
            "id": 1,
            "title": "Test Video",
            "user": "TestUser",
            "upload_year": 2023
        }
    ]

    # Make the request
    response = client.get("/api/videos")
    
    # Check that the service was called
    mock_video_service.get_videos.assert_called_once_with(None, None, None)
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data
    assert len(data["videos"]) == 1
    assert data["videos"][0]["title"] == "Test Video"
    assert data["count"] == 1


def test_get_videos_with_filters(client, mock_video_service):
    """Test the /api/videos endpoint with filters"""
    # Setup mock return value
    mock_video_service.get_videos.return_value = [
        {
            "id": 1,
            "title": "Test Video",
            "user": "TestUser",
            "upload_year": 2023
        }
    ]

    # Make the request with query parameters
    response = client.get("/api/videos?user=TestUser&year=2023&q=Test")
    
    # Check that the service was called with the right parameters
    mock_video_service.get_videos.assert_called_once_with("TestUser", 2023, "Test")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data
    assert len(data["videos"]) == 1


def test_get_video_by_id(client, mock_video_service):
    """Test the /api/videos/{video_id} endpoint"""
    # Setup mock return values
    mock_video_service.get_video_by_id.return_value = {
        "id": 1,
        "title": "Test Video",
        "user": "TestUser"
    }
    mock_video_service.get_related_videos.return_value = []

    # Make the request
    response = client.get("/api/videos/1")
    
    # Check that the service was called
    mock_video_service.get_video_by_id.assert_called_once_with(1)
    mock_video_service.get_related_videos.assert_called_once()
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "video" in data
    assert data["video"]["title"] == "Test Video"
    assert "related_videos" in data


def test_get_video_by_id_not_found(client, mock_video_service):
    """Test the /api/videos/{video_id} endpoint when video is not found"""
    # Setup mock return value
    mock_video_service.get_video_by_id.return_value = None

    # Make the request
    response = client.get("/api/videos/999")
    
    # Check the response
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "Video not found"


def test_get_users(client, mock_video_service):
    """Test the /api/users endpoint"""
    # Setup mock return value
    mock_video_service.get_users.return_value = ["User1", "User2"]

    # Make the request
    response = client.get("/api/users")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 2
    assert "User1" in data["users"]


def test_get_years(client, mock_video_service):
    """Test the /api/years endpoint"""
    # Setup mock return value
    mock_video_service.get_years.return_value = [2021, 2022, 2023]

    # Make the request
    response = client.get("/api/years")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "years" in data
    assert len(data["years"]) == 3
    assert 2022 in data["years"]


def test_get_featured(client, mock_video_service):
    """Test the /api/featured endpoint"""
    # Setup mock return value - update to match what's expected
    mock_video_service.get_random_featured_video.return_value = {
        "id": 1,
        "title": "Nakitofu Video",  # Changed to match expected value
        "user": "TestUser"
    }

    # Make the request
    response = client.get("/api/featured")
    
    # Check the response
    assert response.status_code == 200
    data = response.json()
    assert "featured_video" in data
    assert data["featured_video"]["title"] == "Nakitofu Video"  # Updated assertion


def test_get_featured_no_videos(client, mock_video_service):
    """Test the /api/featured endpoint when no videos are available"""
    # Setup mock return value
    mock_video_service.get_random_featured_video.return_value = None

    # Make the request
    response = client.get("/api/featured")
    
    # Check the response
    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert data["detail"] == "No videos available"


def test_database_error_handling(client, mock_video_service):
    """Test error handling for database access failures"""
    # Setup mock to raise FileNotFoundError
    mock_video_service.get_videos.side_effect = FileNotFoundError("Database not found")

    # Make the request
    response = client.get("/api/videos")
    
    # Check the response
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Database not found" in data["detail"]
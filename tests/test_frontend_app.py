import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

# Add the frontend directory to the path
sys.path.append(str(Path(__file__).parent.parent / "frontend"))

from frontend_app import app, api_request, process_video_data


@pytest.fixture
def mock_httpx_client():
    """Fixture for mocking httpx client"""
    with patch("httpx.AsyncClient") as mock_client:
        # Create AsyncMock for the get method return value
        mock_response = AsyncMock()
        mock_response.json.return_value = {"videos": []}
        mock_response.raise_for_status = AsyncMock()
        
        # Setup the client's get method to return our mock response
        mock_client.return_value.__aenter__.return_value.get.return_value = mock_response
        
        yield mock_client


@pytest.mark.asyncio
async def test_api_request(mock_httpx_client):
    """Test the api_request function"""
    # Call the api_request function
    result = await api_request("/api/videos", {"user": "test"})
    
    # Check that the httpx client was called correctly
    mock_client = mock_httpx_client.return_value.__aenter__.return_value
    mock_client.get.assert_called_once_with(
        "http://localhost:8000/api/videos", 
        params={"user": "test"}, 
        timeout=10.0
    )
    
    # Check the result
    assert result == {"videos": []}


def test_process_video_data_single_video():
    """Test processing a single video dictionary"""
    video = {
        "id": 1,
        "title": "Test Video",
        "image_url": "/data/thumbnails/test.jpg",
        "preview_url": "/data/previews/test.gif"
    }
    
    processed = process_video_data(video)
    
    assert processed["original_image_url"] == "/data/thumbnails/test.jpg"
    assert processed["image_url"] == "/proxy/media?path=/data/thumbnails/test.jpg"
    assert processed["original_preview_url"] == "/data/previews/test.gif"
    assert processed["preview_url"] == "/proxy/media?path=/data/previews/test.gif"


def test_process_video_data_multiple_videos():
    """Test processing a list of video dictionaries"""
    videos = [
        {
            "id": 1,
            "title": "Test Video 1",
            "image_url": "/data/thumbnails/test1.jpg",
            "preview_url": "/data/previews/test1.gif"
        },
        {
            "id": 2,
            "title": "Test Video 2",
            "image_url": "/data/thumbnails/test2.jpg",
            "preview_url": "/data/previews/test2.gif"
        }
    ]
    
    processed = process_video_data(videos)
    
    assert len(processed) == 2
    assert processed[0]["original_image_url"] == "/data/thumbnails/test1.jpg"
    assert processed[0]["image_url"] == "/proxy/media?path=/data/thumbnails/test1.jpg"
    assert processed[1]["original_image_url"] == "/data/thumbnails/test2.jpg"
    assert processed[1]["image_url"] == "/proxy/media?path=/data/thumbnails/test2.jpg"


def test_process_video_data_empty_input():
    """Test processing empty input"""
    assert process_video_data([]) == []
    assert process_video_data(None) is None


@pytest.mark.asyncio
@patch("frontend_app.templates")
@patch("frontend_app.api_request")
async def test_home_route(mock_api_request, mock_templates):
    """Test the home route with mocked dependencies"""
    # Mock the API response
    mock_api_request.return_value = {
        "videos": [
            {"id": 1, "title": "Test Video", "image_url": "/data/test.jpg", "preview_url": "/data/test.gif"}
        ]
    }
    
    # Create a mock request
    mock_request = MagicMock()
    
    # Call the home route
    from frontend_app import home
    await home(mock_request)
    
    # Check that templates.TemplateResponse was called
    mock_templates.TemplateResponse.assert_called_once()
    # Check the template name
    assert mock_templates.TemplateResponse.call_args[0][0] == "index.html"


@pytest.mark.asyncio
@patch("frontend_app.templates")
@patch("frontend_app.api_request")
async def test_watch_video_route(mock_api_request, mock_templates):
    """Test the watch_video route with mocked dependencies"""
    # Mock the API response
    mock_api_request.return_value = {
        "video": {
            "id": 1, 
            "title": "Test Video", 
            "image_url": "/data/test.jpg", 
            "preview_url": "/data/test.gif"
        },
        "related_videos": []
    }
    
    # Create a mock request
    mock_request = MagicMock()
    
    # Call the watch_video route
    from frontend_app import watch_video
    await watch_video(mock_request, 1)
    
    # Check that templates.TemplateResponse was called
    mock_templates.TemplateResponse.assert_called_once()
    # Check the template name
    assert mock_templates.TemplateResponse.call_args[0][0] == "watch.html"

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import sys
from pathlib import Path

# Fix module imports by adjusting path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

# Mock templates before importing
templates_mock = MagicMock()
httpx_mock = MagicMock()

# Path specifically for the module under test
with patch.dict(sys.modules, {
    'fastapi.templating': MagicMock(),
    'httpx': MagicMock(),
}):
    sys.modules['fastapi.templating'].Jinja2Templates = MagicMock(return_value=templates_mock)
    sys.modules['httpx'].AsyncClient = httpx_mock
    
    # Now import the module under test
    from frontend.frontend_app import process_video_data


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
        
        yield mock_client, mock_response

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
async def test_home_route():
    """Test the home route with mocked dependencies"""
    # Mock api_request
    mock_api = AsyncMock()
    mock_api.side_effect = [
        {
            "videos": [
                {"id": 1, "title": "Test Video", "image_url": "/data/test.jpg", "preview_url": "/data/test.gif"}
            ]
        },
        {
            "users": ["TestUser"]
        },
        {
            "years": [2023]
        },
        {
            "featured_video": {"id": 1, "title": "Featured Video"}
        }
    ]
    
    # Mock templates
    mock_templates = MagicMock()
    
    # Mock process_video_data
    mock_process = MagicMock()
    mock_process.return_value = [
        {"id": 1, "title": "Test Video", "image_url": "/proxy/media?path=/data/test.jpg"}
    ]
    
    # Patch the dependencies
    with patch("frontend.frontend_app.api_request", mock_api), \
         patch("frontend.frontend_app.templates", mock_templates), \
         patch("frontend.frontend_app.process_video_data", mock_process):
        
        # Import the home function
        from frontend.frontend_app import home
        
        # Create a mock request
        mock_request = MagicMock()
        
        # Call the home route
        await home(mock_request)
        
        # Check that templates.TemplateResponse was called
        mock_templates.TemplateResponse.assert_called_once()
        # Check the template name
        assert mock_templates.TemplateResponse.call_args[0][0] == "index.html"
        # Check that context has the right keys
        context = mock_templates.TemplateResponse.call_args[0][1]
        assert "request" in context
        assert "videos" in context


@pytest.mark.asyncio
async def test_watch_video_route():
    """Test the watch_video route with mocked dependencies"""
    # Mock api_request
    mock_api = AsyncMock()
    mock_api.return_value = {
        "video": {
            "id": 1, 
            "title": "Test Video", 
            "image_url": "/data/test.jpg", 
            "preview_url": "/data/test.gif"
        },
        "related_videos": []
    }
    
    # Mock templates
    mock_templates = MagicMock()
    
    # Mock process_video_data
    mock_process = MagicMock()
    mock_process.side_effect = lambda x: x  # Just return the input
    
    # Patch the dependencies
    with patch("frontend.frontend_app.api_request", mock_api), \
         patch("frontend.frontend_app.templates", mock_templates), \
         patch("frontend.frontend_app.process_video_data", mock_process):
        
        # Import the watch_video function
        from frontend.frontend_app import watch_video
        
        # Create a mock request
        mock_request = MagicMock()
        
        # Call the watch_video route
        await watch_video(mock_request, 1)
        
        # Check that templates.TemplateResponse was called
        mock_templates.TemplateResponse.assert_called_once()
        # Check the template name
        assert mock_templates.TemplateResponse.call_args[0][0] == "watch.html"
        # Check that context has the right keys
        context = mock_templates.TemplateResponse.call_args[0][1]
        assert "request" in context
        assert "video" in context
        assert "related_videos" in context
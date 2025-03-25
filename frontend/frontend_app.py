"""
Video Preview Application - Frontend Server
==========================================

Overview:
---------
This module implements the web interface for the Video Preview Application using FastAPI,
serving HTML templates and proxying media requests to the backend API.

The frontend provides:
- A browsable gallery of video previews
- Individual video watch pages
- Search and filtering functionality
- Media proxying to seamlessly serve content from the backend

Key Components:
--------------
- FastAPI web framework for serving the interface
- Jinja2 templating for HTML rendering
- HTTPX client for backend API communication
- Proxy handlers for media content
"""
from fastapi import FastAPI, Request, Form, Query, HTTPException
from fastapi.responses import Response, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from typing import Optional, Dict, Any, List, Union
import os
import uvicorn
import httpx
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get the current directory where frontend_app.py is located
current_dir = os.path.dirname(os.path.abspath(__file__))
logger.debug(f"Current directory: {current_dir}")

# Create FastAPI app
app = FastAPI(title="VideoFlix Web Interface")

# Static files and templates with absolute paths
static_path = os.path.join(current_dir, "static")
templates_path = os.path.join(current_dir, "templates")

# Log template path information
logger.debug(f"Templates path: {templates_path}")
logger.debug(f"Templates directory exists: {os.path.exists(templates_path)}")
if os.path.exists(templates_path):
    logger.debug(f"Templates directory contents: {os.listdir(templates_path)}")

# Mount static files directory using absolute path
app.mount("/static", StaticFiles(directory=static_path), name="static")
templates = Jinja2Templates(directory=templates_path)

# Backend API URL (can be configured for different environments)
API_URL = os.environ.get("API_URL", "http://localhost:8000")
logger.debug(f"Using API URL: {API_URL}")

async def api_request(endpoint: str, params: dict = None):
    """
    Make a request to the backend API.
    
    Args:
        endpoint: API endpoint path (starting with /)
        params: Optional query parameters
        
    Returns:
        JSON response from the API
        
    Raises:
        HTTPException: If the API request fails
    """
    logger.debug(f"Making API request to: {API_URL}{endpoint}")
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_URL}{endpoint}", params=params, timeout=10.0)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error: {str(e)}")
            raise HTTPException(status_code=e.response.status_code, 
                               detail=f"API error: {str(e)} - URL: {API_URL}{endpoint}")
        except httpx.RequestError as e:
            logger.error(f"Request Error: {str(e)}")
            raise HTTPException(status_code=500, 
                               detail=f"API request error: {str(e)} - URL: {API_URL}{endpoint}")
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise HTTPException(status_code=500, 
                               detail=f"Unexpected error: {str(e)} - URL: {API_URL}{endpoint}")

def process_video_data(videos: Union[Dict[str, Any], List[Dict[str, Any]]]) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """
    Process video data to convert backend paths to frontend proxy paths.
    
    This function transforms direct backend media paths to go through
    the frontend proxy, allowing media to be served seamlessly.
    
    Args:
        videos: Video data dictionary or list of video dictionaries
        
    Returns:
        Processed video data with updated media paths
    """
    if not videos:
        return videos
        
    # Handle both single video and list of videos
    if isinstance(videos, dict):
        videos_list = [videos]
    else:
        videos_list = videos
        
    for video in videos_list:
        # Convert image URL to proxy path
        if video.get('image_url'):
            original_path = video['image_url']
            video['original_image_url'] = original_path
            video['image_url'] = f"/proxy/media?path={original_path}"
            
        # Convert preview URL to proxy path
        if video.get('preview_url'):
            original_path = video['preview_url']
            video['original_preview_url'] = original_path
            video['preview_url'] = f"/proxy/media?path={original_path}"
            
    # Return in the same format as input
    if isinstance(videos, dict):
        return videos_list[0]
    else:
        return videos_list

#
# Route Handlers
#

@app.get("/")
async def home(
    request: Request, 
    user: Optional[str] = None,
    year: Optional[int] = None,
    q: Optional[str] = None
):
    """
    Render the home page with videos and filters.
    
    This page shows a gallery of video previews with filtering options.
    
    Args:
        request: FastAPI request object
        user: Optional filter for creator/user
        year: Optional filter for upload year
        q: Optional search query
    """
    # Prepare filter parameters for API request
    params = {}
    if user:
        params["user"] = user
    if year:
        params["year"] = year
    if q:
        params["q"] = q
    
    try:
        logger.debug(f"Home route accessed with params: {params}")
        
        # Get videos from API
        logger.debug(f"Fetching videos from: {API_URL}/api/videos")
        videos_data = await api_request("/api/videos", params)
        videos = videos_data["videos"]
        logger.debug(f"Received {len(videos)} videos")
        
        try:
            # Get users and years for filters
            users_data = await api_request("/api/users")
            users = users_data["users"]
            logger.debug(f"Received users: {users}")
        except Exception as e:
            logger.warning(f"Failed to fetch users: {str(e)}")
            # Fall back to extracting users from videos
            users = list(set(v.get("user") for v in videos if v.get("user")))
            logger.debug(f"Extracted users from videos: {users}")
        
        try:
            years_data = await api_request("/api/years")
            years = years_data["years"]
            logger.debug(f"Received years: {years}")
        except Exception as e:
            logger.warning(f"Failed to fetch years: {str(e)}")
            # Fall back to extracting years from videos
            years = list(set(v.get("upload_year") for v in videos if v.get("upload_year")))
            logger.debug(f"Extracted years from videos: {years}")
        
        try:
            # Get featured video
            featured_data = await api_request("/api/featured")
            featured_video = featured_data.get("featured_video")
            logger.debug(f"Received featured video: {featured_video}")
        except Exception as e:
            logger.warning(f"Failed to fetch featured video: {str(e)}")
            # Fall back to first video as featured
            featured_video = videos[0] if videos else None
            logger.debug(f"Using first video as featured: {featured_video}")
        
        # Process video data to ensure correct paths
        videos = process_video_data(videos)
        if featured_video:
            featured_video = process_video_data(featured_video)
        
        return templates.TemplateResponse(
            "index.html", 
            {
                "request": request, 
                "videos": videos,
                "featured_video": featured_video,
                "users": users,
                "years": years,
                "current_user": user,
                "current_year": year,
                "search_query": q,
                "backend_url": API_URL,
            }
        )
    except Exception as e:
        logger.error(f"Error in home route: {str(e)}")
        # Return the error template with detailed error message
        return templates.TemplateResponse(
            "error_template.html",
            {
                "request": request,
                "error_message": f"Error accessing API: {str(e)}"
            }
        )

@app.get("/watch/{video_id}")
async def watch_video(request: Request, video_id: int):
    """
    Render the video watch page for a specific video.
    
    Args:
        request: FastAPI request object
        video_id: ID of the video to watch
    """
    try:
        logger.debug(f"Watch route accessed for video ID: {video_id}")
        
        # Get video and related videos from API
        video_data = await api_request(f"/api/videos/{video_id}")
        
        # Process video data to ensure correct paths
        video = process_video_data(video_data["video"])
        related_videos = process_video_data(video_data.get("related_videos", []))
        
        return templates.TemplateResponse(
            "watch.html", 
            {
                "request": request, 
                "video": video,
                "related_videos": related_videos,
                "backend_url": API_URL,
            }
        )
    except Exception as e:
        logger.error(f"Error in watch route: {str(e)}")
        return templates.TemplateResponse(
            "error_template.html",
            {
                "request": request,
                "error_message": f"Error accessing video: {str(e)}"
            }
        )

@app.get("/proxy/media")
async def proxy_media(request: Request, path: str):
    """
    Proxy media requests to the backend.
    
    This route handles media requests by fetching them from the backend
    and passing them through to the client, avoiding CORS issues.
    
    Args:
        request: FastAPI request object
        path: The path to proxy (starting with /data/)
    """
    logger.debug(f"Media proxy requested for path: {path}")
    
    full_url = f"{API_URL}{path}"
    logger.debug(f"Proxying request to: {full_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            # Forward the request to the backend
            response = await client.get(full_url, timeout=15.0)
            
            # Forward the response back to the client
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.headers.get("content-type")
            )
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error when proxying media: {str(e)}")
            return Response(
                content=f"Error fetching media: {str(e)}",
                status_code=e.response.status_code if hasattr(e, 'response') else 500,
                media_type="text/plain"
            )
        except Exception as e:
            logger.error(f"Error when proxying media: {str(e)}")
            return Response(
                content=f"Error fetching media: {str(e)}",
                status_code=500,
                media_type="text/plain"
            )

@app.get("/data/{path:path}")
async def direct_proxy(request: Request, path: str):
    """
    Direct proxy for backend data paths.
    
    Useful for when paths are hardcoded in templates or for development.
    
    Args:
        request: FastAPI request object
        path: The path segment after /data/
    """
    full_path = f"/data/{path}"
    logger.debug(f"Direct proxy requested for: {full_path}")
    return await proxy_media(request, path=full_path)

@app.get("/debug")
async def debug_route(request: Request):
    """
    Simple debug route to test template rendering.
    
    Useful for troubleshooting template loading issues.
    """
    logger.debug("Debug route accessed")
    return templates.TemplateResponse(
        "error_template.html",
        {
            "request": request,
            "error_message": "Debug route is working correctly. Templates are being found."
        }
    )

@app.get("/test-api")
async def test_api():
    """
    Test API connection and configuration.
    
    Returns diagnostic information about the frontend setup.
    """
    logger.debug("Test API route accessed")
    return {
        "status": "frontend running", 
        "api_url": API_URL,
        "current_dir": current_dir,
        "templates_path": templates_path,
        "templates_exist": os.path.exists(templates_path),
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring.
    
    Used by monitoring systems to verify service health.
    """
    return {"status": "healthy"}

#
# Error Handlers
#

@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException):
    """
    Handle 404 errors with a user-friendly template.
    """
    logger.warning(f"404 error for path: {request.url.path}")
    return templates.TemplateResponse(
        "error_template.html",
        {
            "request": request,
            "error_message": f"The requested resource was not found: {request.url.path}"
        },
        status_code=404
    )

@app.exception_handler(500)
async def server_error_handler(request: Request, exc: HTTPException):
    """
    Handle 500 errors with a user-friendly template.
    """
    logger.error(f"500 error for path: {request.url.path}")
    return templates.TemplateResponse(
        "error_template.html",
        {
            "request": request,
            "error_message": f"An internal server error occurred: {str(exc)}"
        },
        status_code=500
    )

# For running the frontend server standalone
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8001))
    logger.info(f"Starting frontend server on port {port}")
    uvicorn.run("frontend_app:app", host="0.0.0.0", port=port, reload=True)
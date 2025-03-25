"""
Video Preview Application - Backend API
======================================

This module implements the REST API endpoints for the Video Preview Application
using FastAPI. It provides access to video metadata, previews, and thumbnails.

The API serves:
- Video listings with filtering options
- Individual video details
- Related video recommendations
- Metadata for filtering (users, years)
- Featured video selection
- Static media files from the data directory
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from typing import List, Dict, Optional, Any
import os
import sys
import uvicorn

# Add the current directory to the path so we can import local modules
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from video_service import VideoService

# Create FastAPI app
app = FastAPI(title="Video Preview API")

# Configure CORS for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update this with specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory config
DATA_DIR = os.environ.get("DATA_DIR", os.path.join(os.path.dirname(current_dir), "data"))

# Initialize video service
video_service = VideoService(data_dir=DATA_DIR)

# Mount the data directory for static access to previews and thumbnails
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

#
# API Endpoints
#

@app.get("/api/videos")
async def get_videos(
    user: Optional[str] = None,
    year: Optional[int] = None,
    q: Optional[str] = None
):
    """
    Get a list of videos with optional filtering.
    
    This endpoint returns video metadata including paths to previews and thumbnails.
    
    Args:
        user: Filter by username/creator
        year: Filter by upload year
        q: Search query for title or description
        
    Returns:
        dict: Dictionary containing videos and count
        
    Raises:
        HTTPException: If database access fails
    """
    try:
        videos = video_service.get_videos(user, year, q)
        return {"videos": videos, "count": len(videos)}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/videos/{video_id}")
async def get_video(video_id: int):
    """
    Get a specific video by ID.
    
    This endpoint returns detailed information about a single video,
    along with a list of related videos.
    
    Args:
        video_id: The ID of the video to retrieve
        
    Returns:
        dict: Video data and related videos
        
    Raises:
        HTTPException: If video not found or database access fails
    """
    try:
        video = video_service.get_video_by_id(video_id)
        if not video:
            raise HTTPException(status_code=404, detail="Video not found")
        
        # Get related videos
        related_videos = video_service.get_related_videos(video)
        
        return {
            "video": video,
            "related_videos": related_videos
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/users")
async def get_users():
    """
    Get list of all users/creators in the database.
    
    This endpoint is used for populating filter dropdowns in the UI.
    
    Returns:
        dict: Dictionary containing list of users
        
    Raises:
        HTTPException: If database access fails
    """
    try:
        return {"users": video_service.get_users()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/years")
async def get_years():
    """
    Get list of all upload years in the database.
    
    This endpoint is used for populating filter dropdowns in the UI.
    
    Returns:
        dict: Dictionary containing list of years
        
    Raises:
        HTTPException: If database access fails
    """
    try:
        return {"years": video_service.get_years()}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/featured")
async def get_featured():
    """
    Get a random featured video for the homepage.
    
    Returns:
        dict: Featured video data
        
    Raises:
        HTTPException: If no videos available or database access fails
    """
    try:
        featured = video_service.get_random_featured_video()
        if not featured:
            raise HTTPException(status_code=404, detail="No videos available")
        return {"featured_video": featured}
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=str(e))

# For running the API server standalone
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend_api:app", host="0.0.0.0", port=port, reload=True)
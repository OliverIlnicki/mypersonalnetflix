#%%
from fastapi import FastAPI, Request, Form, Query
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import random
import os
import json
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, parse_qs

#%%
# Create FastAPI app
app = FastAPI(title="Video Preview App")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Data directory (where youtube-preview-gif-creator.py saves its output)
DATA_DIR = os.environ.get("DATA_DIR", "./data")

# Mount static files directory for our app assets
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount the data directory for previews and thumbnails
app.mount("/data", StaticFiles(directory=DATA_DIR), name="data")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Helper function to connect to SQLite database
def get_db_connection():
    db_path = os.path.join(DATA_DIR, "videos.db")
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Database not found at {db_path}. Run youtube-preview-gif-creator.py first.")
    return sqlite3.connect(db_path)

# Helper function to extract YouTube video ID
def extract_youtube_id(url):
    if not url:
        return None
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[1].split('?')[0]
    elif 'youtube.com/watch' in url:
        parsed_url = urlparse(url)
        query_params = parse_qs(parsed_url.query)
        if 'v' in query_params:
            return query_params['v'][0]
    return None

# Load videos from the database
def load_videos(user=None, year=None, search_query=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = "SELECT * FROM videos WHERE 1=1"
    params = []
    
    if user:
        query += " AND user = ?"
        params.append(user)
    
    if year:
        query += " AND upload_year = ?"
        params.append(year)
        
    if search_query:
        query += " AND (title LIKE ? OR description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    
    cursor.execute(query, params)
    columns = [description[0] for description in cursor.description]
    videos = []
    
    for row in cursor.fetchall():
        video = dict(zip(columns, row))
        # Add the full path for thumbnail and preview
        if video['thumb_path']:
            video['image_url'] = f"/data/{video['thumb_path']}"
        if video['vid_preview_path']:
            video['preview_url'] = f"/data/{video['vid_preview_path']}"
        
        # Extract YouTube ID if it's a YouTube URL
        if video['url'] and ('youtube.com' in video['url'] or 'youtu.be' in video['url']):
            video['youtube_id'] = extract_youtube_id(video['url'])
        
        # Set default preview_type if not in database
        if 'preview_type' not in video or not video['preview_type']:
            # Check the file extension to make a guess
            if video['vid_preview_path'] and video['vid_preview_path'].lower().endswith('.mp4'):
                video['preview_type'] = 'mp4'
            else:
                video['preview_type'] = 'gif'
                
        videos.append(video)
    
    conn.close()
    return videos

# Get list of available users
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT user FROM videos WHERE user != ''")
    users = [row[0] for row in cursor.fetchall()]
    conn.close()
    return users

# Get list of available years
def get_years():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT upload_year FROM videos WHERE upload_year IS NOT NULL")
    years = [row[0] for row in cursor.fetchall()]
    conn.close()
    return sorted(years)

# Routes
@app.get("/")
async def home(
    request: Request, 
    user: Optional[str] = None,
    year: Optional[int] = None,
    q: Optional[str] = None
):
    try:
        # Load videos with optional filters
        videos = load_videos(user, year, q)
        
        # Get available filters
        users = get_users()
        years = get_years()
        
        # Select a random featured video
        featured_video = random.choice(videos) if videos else None
        
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
                "search_query": q
            }
        )
    except FileNotFoundError as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": str(e)
            }
        )

@app.get("/watch/{video_id}")
async def watch_video(request: Request, video_id: int):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return {"error": "Video not found"}
            
        video = dict(zip(columns, row))
        # Add the full path for thumbnail and preview
        if video['thumb_path']:
            video['image_url'] = f"/data/{video['thumb_path']}"
        if video['vid_preview_path']:
            video['preview_url'] = f"/data/{video['vid_preview_path']}"
            
        # Extract YouTube ID if it's a YouTube URL
        if video['url'] and ('youtube.com' in video['url'] or 'youtu.be' in video['url']):
            video['youtube_id'] = extract_youtube_id(video['url'])
            
        # Set default preview_type if not in database
        if 'preview_type' not in video or not video['preview_type']:
            # Check the file extension to make a guess
            if video['vid_preview_path'] and video['vid_preview_path'].lower().endswith('.mp4'):
                video['preview_type'] = 'mp4'
            else:
                video['preview_type'] = 'gif'
        
        # Get related videos (simple implementation: same user or year)
        related_videos = load_videos(user=video['user'])[:5]  # Limit to 5 related videos
        
        return templates.TemplateResponse(
            "watch.html", 
            {
                "request": request, 
                "video": video,
                "related_videos": related_videos
            }
        )
    except FileNotFoundError as e:
        return templates.TemplateResponse(
            "error.html",
            {
                "request": request,
                "error_message": str(e)
            }
        )

# API endpoints for programmatic access
@app.get("/api/videos")
async def api_videos(
    user: Optional[str] = None,
    year: Optional[int] = None,
    q: Optional[str] = None
):
    try:
        videos = load_videos(user, year, q)
        return {"videos": videos, "count": len(videos)}
    except FileNotFoundError as e:
        return {"error": str(e)}

@app.get("/api/users")
async def api_users():
    try:
        return {"users": get_users()}
    except FileNotFoundError as e:
        return {"error": str(e)}

@app.get("/api/years")
async def api_years():
    try:
        return {"years": get_years()}
    except FileNotFoundError as e:
        return {"error": str(e)}

# Use Heroku's assigned port or default to 8000
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port)
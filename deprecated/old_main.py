#%%
from fastapi import FastAPI, Request, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn
import random
import os
from urllib.parse import urlparse, parse_qs
#%%
# Create FastAPI app
app = FastAPI(title="Netflix Clone API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Setup templates
templates = Jinja2Templates(directory="templates")

# Sample data
videos = [
    {"url": "https://youtu.be/tfMCXjUQhnI", "title": "Impro in the Machine", "image_url": "https://i9.ytimg.com/vi/tfMCXjUQhnI/mqdefault.jpg?sqp=CIzXpr4G-oaymwEmCMACELQB8quKqQMa8AEB-AH-CYAC0AWKAgwIABABGFAgXihlMA8=&rs=AOn4CLC7z42l6I0UqOM8reW1_H-j3lbffg"},
    {"url": "https://youtu.be/ZtwcrVFeYqQ", "title": "Bürokrieger", "image_url": "https://i9.ytimg.com/vi/ZtwcrVFeYqQ/mqdefault.jpg?v=6777af97&sqp=CIzXpr4G&rs=AOn4CLDA-SDpsuoBylyOO_PeRAY-7I_S9A"},
    {"url": "https://youtu.be/tBeG7vmhqdk", "title": "Nakitofu", "image_url": "https://i9.ytimg.com/vi/tBeG7vmhqdk/mqdefault.jpg?sqp=CIzXpr4G-oaymwEmCMACELQB8quKqQMa8AEB-AH-CYAC0AWKAgwIABABGHIgUSg8MA8=&rs=AOn4CLCtgH29knar_hLwOQL-VWT92BtD1w"},
    {"url": "https://youtu.be/_w92WhpCp1U", "title": "War Mindset", "image_url": "https://i9.ytimg.com/vi/_w92WhpCp1U/mqdefault.jpg?v=645e284e&sqp=CIzXpr4G&rs=AOn4CLBbJlnbG2aUvfLF6wBCYcaWK5kkjw"},
    {"url": "https://www.youtube.com/watch?v=EV2Lz61blFI", "title": "Filmproduktion: Von der Magie des Pilgerns - Wallfahrt Much-Werl", "image_url": "https://i.ytimg.com/vi_webp/EV2Lz61blFI/mqdefault.webp?v=6738e271"},
    {"url": "https://youtu.be/U6nicqS7A9c", "title": "Tee[Werbung]", "image_url": "https://i9.ytimg.com/vi/U6nicqS7A9c/mqdefault.jpg?sqp=CIzXpr4G-oaymwEmCMACELQB8quKqQMa8AEB-AH-CYAC0AWKAgwIABABGGUgUShEMA8=&rs=AOn4CLD5Zy7HpmAwbBDGW-VMI1bwgJIH-A"},
    {"url": "https://youtu.be/idtarKCSLB8", "title": "Whispers in the Shelves", "image_url": "https://i9.ytimg.com/vi/idtarKCSLB8/mqdefault.jpg?sqp=CIzXpr4G-oaymwEmCMACELQB8quKqQMa8AEB-AH-CYAC0AWKAgwIABABGGUgWihNMA8=&rs=AOn4CLCItmsc57MfQIF8ZSXPIGcEmUiO7A"},
    {"url": "https://www.youtube.com/watch?v=Q5sdtZO1GG4", "title": "Licht unter der Brücke", "image_url": "https://i.ytimg.com/vi_webp/Q5sdtZO1GG4/mqdefault.webp?v=63e4ae5d"},
    {"url": "https://www.youtube.com/watch?v=-3Glp64HmTI", "title": "Ausgangspunkt", "image_url": "https://i.ytimg.com/vi/-3Glp64HmTI/mqdefault.jpg?sqp=-oaymwEmCMACELQB8quKqQMa8AEB-AH-CYAC0AWKAgwIABABGGUgZShlMA8=&rs=AOn4CLAGu6yHHi7I6lAkLhr37rn0DNvU4Q"},
    {"url": "https://www.youtube.com/watch?v=pBIIYHavH20", "title": "Mobile Demo Fabrik auf der Hannover Messe 2022", "image_url": "https://i.ytimg.com/vi_webp/pBIIYHavH20/mqdefault.webp?v=63bd0b97"}
]

# Helper function to extract YouTube video ID
def extract_youtube_id(url):
    if 'youtu.be/' in url:
        return url.split('youtu.be/')[1]
    elif 'youtube.com/watch' in url:
        parsed_url = urlparse(url)
        return parse_qs(parsed_url.query)['v'][0]
    return None

# Add video IDs to each video
for video in videos:
    video['youtube_id'] = extract_youtube_id(video['url'])

# Routes
@app.get("/")
async def home(request: Request):
    # Select a random featured video
    featured_video = random.choice(videos)
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "videos": videos,
            "featured_video": featured_video
        }
    )

@app.get("/search")
async def search(request: Request, q: str = ""):
    # Filter videos by search query
    if q:
        filtered_videos = [v for v in videos if q.lower() in v['title'].lower()]
    else:
        filtered_videos = videos
    
    # Select a random featured video from filtered videos or use first video
    featured_video = random.choice(filtered_videos) if filtered_videos else None
    
    return templates.TemplateResponse(
        "index.html", 
        {
            "request": request, 
            "videos": filtered_videos,
            "featured_video": featured_video,
            "search_query": q
        }
    )

@app.get("/watch/{video_id}")
async def watch_video(request: Request, video_id: int):
    if 0 <= video_id < len(videos):
        video = videos[video_id]
        return templates.TemplateResponse(
            "watch.html", 
            {
                "request": request, 
                "video": video
            }
        )
    return {"error": "Video not found"}

# Use Heroku's assigned port
port = int(os.environ.get("PORT", 8000))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=port)
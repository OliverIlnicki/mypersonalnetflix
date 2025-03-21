"""
This script downloads videos from YouTube and other sources, extracts metadata, and creates GIF previews. Previews are stored in files and metadata is stored in an SQLite database. 
"""
#%% 
#Import common dependencies
import os
import sys
import random
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import argparse
import logging
import requests
import pickle
from typing import Optional, Tuple, Dict, List, Any

#%% 
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
# Import external dependencies needed for preview creation
import pytubefix
from pytubefix import YouTube
import moviepy.video.VideoClip
from src.youtube_url_checker import  check_youtube_video_accessible
from src.youtube_source import YouTubeSource
from src.local_source import LocalFileSource
from src.base_source import VideoSource
#%%
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

#%%
class VideoPreviewCreator:
    """
    Main class that handles creation of video previews
    """
    def __init__(self, output_dir: str, db_path: Optional[str] = None):
        self.output_dir = output_dir
        self.db_path = db_path or os.path.join(output_dir, "videos.db")
        self.db_conn = None
        self.video_sources = {}
        
        # Register available video sources
        self.register_source("youtube", YouTubeSource())
        self.register_source("local", LocalFileSource())
        
        # Ensure directories exist
        self._create_directories()
        
        # Initialize database
        self.init_database()
    
    def register_source(self, name: str, source: VideoSource) -> None:
        """
        Register a new video source
        """
        self.video_sources[name] = source
        logger.info(f"Registered video source: {name}")
    
    def _create_directories(self) -> None:
        """
        Create necessary directories
        """
        # Main output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")
        
        # Temporary videos directory
        self.temp_dir = os.path.join(self.output_dir, "temp_videos")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            
        # Thumbnails directory
        self.thumbnails_dir = os.path.join(self.output_dir, "thumbnails")
        if not os.path.exists(self.thumbnails_dir):
            os.makedirs(self.thumbnails_dir)
            logger.info(f"Created thumbnails directory: {self.thumbnails_dir}")
            
        # GIF directory
        self.gif_dir = os.path.join(self.output_dir, "previews")
        if not os.path.exists(self.gif_dir):
            os.makedirs(self.gif_dir)
            logger.info(f"Created GIF previews directory: {self.gif_dir}")
    
    def init_database(self) -> None:
        """
        Initialize SQLite database with the required schema
        """
        try:
            self.db_conn = sqlite3.connect(self.db_path)
            cursor = self.db_conn.cursor()
            
            # Create videos table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                url TEXT UNIQUE,
                source TEXT,
                title TEXT,
                description TEXT,
                thumb_path TEXT,
                vid_preview_path TEXT,
                upload_year INTEGER,
                content_hash TEXT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Add content_hash column if it doesn't exist (for upgrades)
            try:
                cursor.execute("SELECT content_hash FROM videos LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE videos ADD COLUMN content_hash TEXT")
                logger.info("Added content_hash column to database schema")
            
            # Create an index on content_hash for faster duplicate checking
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON videos (content_hash)")
            
            self.db_conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None
    
    def create_gif_preview(self, video_path: str, duration: int = 30) -> Optional[str]:
        """
        Create a GIF preview from a representative part of the video
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None
                
            clip = VideoFileClip(video_path)
            video_duration = clip.duration
            
            # Skip the first and last 20% of the video to avoid intros and outros
            start_threshold = video_duration * 0.2
            end_threshold = video_duration * 0.8
            
            # Select a random start point in the middle 60% of the video
            if video_duration <= duration:
                # If video is shorter than desired duration, use the whole video
                start_time = 0
                actual_duration = video_duration
            else:
                # Make sure we don't go beyond the end of the video
                max_start = min(end_threshold - duration, video_duration - duration)
                min_start = max(start_threshold, 0)
                
                if max_start <= min_start:
                    start_time = 0
                else:
                    start_time = random.uniform(min_start, max_start)
                    
                actual_duration = min(duration, video_duration - start_time)
                
            # Extract the subclip and create a GIF
            subclip = clip.subclip(start_time, start_time + actual_duration)
            
            # Resize to lower resolution for GIF (320px width)
            subclip = subclip.resize(width=320)
            
            # Get the base filename without extension
            video_filename = os.path.basename(video_path)
            gif_filename = os.path.splitext(video_filename)[0] + ".gif"
            gif_path = os.path.join(self.gif_dir, gif_filename)
            
            # Write the GIF with reduced framerate for smaller file size
            subclip.write_gif(gif_path, fps=10)
            
            # Close the clips to free resources
            subclip.close()
            clip.close()
            
            logger.info(f"Created GIF preview: {gif_path}")
            return gif_path
        except Exception as e:
            logger.error(f"Error creating GIF: {str(e)}")
            if 'clip' in locals():
                clip.close()
            return None
    
    def is_duplicate(self, url: str, content_hash: str) -> bool:
        """
        Check if a video is already in the database by URL or content hash
        """
        if not self.db_conn:
            return False
            
        try:
            cursor = self.db_conn.cursor()
            
            # First check URL (exact duplicate)
            cursor.execute("SELECT id FROM videos WHERE url = ?", (url,))
            if cursor.fetchone():
                logger.info(f"Skipping duplicate URL: {url}")
                return True
            
            # Then check content hash (same video from different source)
            if content_hash:
                cursor.execute("SELECT id, url FROM videos WHERE content_hash = ?", (content_hash,))
                result = cursor.fetchone()
                if result:
                    logger.info(f"Skipping duplicate content (hash: {content_hash}), already exists as URL: {result[1]}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            return False
    
    def save_to_database(self, video_info: Dict[str, Any]) -> Optional[int]:
        """
        Save a video record to the SQLite database
        """
        if not self.db_conn:
            logger.error("Database connection not available")
            return None
            
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO videos 
            (user, url, source, title, description, thumb_path, vid_preview_path, upload_year, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_info['user'],
                video_info['url'],
                video_info['source'],
                video_info['title'],
                video_info['description'],
                video_info['thumb_path'],
                video_info['vid_preview_path'],
                video_info['upload_year'],
                video_info.get('content_hash', '')
            ))
            self.db_conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return None
    
    def process_url(self, url: str, username: str = "") -> Optional[Dict[str, Any]]:
        """
        Process a single URL and create a GIF preview
        """
        # Determine the appropriate video source
        source_name = None
        source = None
        
        for name, src in self.video_sources.items():
            if src.is_valid_url(url):
                source_name = name
                source = src
                break
        
        if not source:
            logger.error(f"No compatible video source found for URL: {url}")
            return None
        
        # Download the video and thumbnail, get metadata
        video_path, thumbnail_path, video_title, video_description, upload_year = source.download_video(url, self.temp_dir)
        if not video_path:
            logger.error(f"Failed to download video from {url}")
            return None
        
        # Generate content hash for duplicate detection
        content
"""
Video Preview Application - Backend Service Layer
================================================

This module provides the service layer for video-related operations, acting as an
intermediary between the API endpoints and the database. It handles data retrieval,
transformation, and business logic for video previews and metadata.

The VideoService class encapsulates all video data operations including:
- Database connections and queries
- Video metadata enhancement
- YouTube video ID extraction
- Path resolution for media assets
- Related video discovery
"""
import os
import random
import sqlite3
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import List, Dict, Optional, Any, Union

class VideoService:
    """
    Service class that provides data access and business logic for video operations.
    
    This class handles database interactions, path resolution, and data enhancement
    for the video preview application.
    """
    
    def __init__(self, data_dir: str = "./data"):
        """
        Initialize the video service with a data directory.
        
        Args:
            data_dir: Path to the data directory containing videos.db and media assets
        """
        self.data_dir = data_dir
        
    def _get_db_connection(self) -> sqlite3.Connection:
        """
        Establish a connection to the SQLite database.
        
        Returns:
            sqlite3.Connection: Database connection object
        
        Raises:
            FileNotFoundError: If the database file doesn't exist at the expected location
        """
        db_path = os.path.join(self.data_dir, "videos.db")
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database not found at {db_path}. Please run the ETL process first.")
        return sqlite3.connect(db_path)
    
    def extract_youtube_id(self, url: Optional[str]) -> Optional[str]:
        """
        Extract YouTube video ID from a URL.
        
        Handles both youtu.be short links and youtube.com/watch formats.
        
        Args:
            url: YouTube URL string
            
        Returns:
            str: YouTube video ID or None if not a valid YouTube URL
        """
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
    
    def get_video_path(self, relative_path: Optional[str]) -> Optional[str]:
        """
        Convert a relative path to a URL path for the frontend.
        
        This ensures media files can be properly accessed through the API.
        
        Args:
            relative_path: Relative path to the asset from the data directory
            
        Returns:
            str: URL path for the frontend (/data/...)
        """
        if not relative_path:
            return None
        return f"/data/{relative_path}"
    
    def enhance_video_data(self, video: Dict[str, Any]) -> Dict[str, Any]:
        """
        Enhance video data with additional fields needed by the frontend.
        
        This function adds URL paths, extracts YouTube IDs, and sets
        default values for missing fields.
        
        Args:
            video: Raw video data dictionary from the database
            
        Returns:
            dict: Enhanced video data with additional fields
        """
        # Add the full path for thumbnail and preview
        if video.get('thumb_path'):
            video['image_url'] = self.get_video_path(video['thumb_path'])
        if video.get('vid_preview_path'):
            video['preview_url'] = self.get_video_path(video['vid_preview_path'])
        
        # Extract YouTube ID if it's a YouTube URL
        if video.get('url') and ('youtube.com' in video['url'] or 'youtu.be' in video['url']):
            video['youtube_id'] = self.extract_youtube_id(video['url'])
        
        # Set default preview_type if not in database
        if 'preview_type' not in video or not video['preview_type']:
            # Check the file extension to make a guess
            if video.get('vid_preview_path') and video['vid_preview_path'].lower().endswith('.mp4'):
                video['preview_type'] = 'mp4'
            else:
                video['preview_type'] = 'gif'
                
        return video
    
    def get_videos(self, user: Optional[str] = None, 
                  year: Optional[int] = None, 
                  search_query: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve videos from the database with optional filtering.
        
        Args:
            user: Filter by username/creator
            year: Filter by upload year
            search_query: Filter by search terms in title or description
            
        Returns:
            list: List of enhanced video dictionaries matching filters
        """
        conn = self._get_db_connection()
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
            videos.append(self.enhance_video_data(video))
        
        conn.close()
        return videos
    
    def get_video_by_id(self, video_id: int) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific video by ID.
        
        Args:
            video_id: The database ID of the video to retrieve
            
        Returns:
            dict: Enhanced video data dictionary or None if not found
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
        columns = [description[0] for description in cursor.description]
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
            
        video = dict(zip(columns, row))
        return self.enhance_video_data(video)
    
    def get_users(self) -> List[str]:
        """
        Get list of all unique users in the database.
        
        Returns:
            list: List of usernames/creators
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT user FROM videos WHERE user != ''")
        users = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return users
    
    def get_years(self) -> List[int]:
        """
        Get list of all upload years in the database.
        
        Returns:
            list: List of years in ascending order
        """
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT DISTINCT upload_year FROM videos WHERE upload_year IS NOT NULL")
        years = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        return sorted(years)
    
    def get_random_featured_video(self) -> Optional[Dict[str, Any]]:
        """
        Get a random video to feature on the homepage.
        
        Returns:
            dict: Random enhanced video data or None if no videos exist
        """
        videos = self.get_videos()
        if not videos:
            return None
        return random.choice(videos)
    
    def get_related_videos(self, video: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get videos related to the given video.
        
        Currently returns other videos by the same creator,
        but could be extended for more sophisticated recommendations.
        
        Args:
            video: The main video to find related content for
            limit: Maximum number of related videos to return
            
        Returns:
            list: List of related video dictionaries
        """
        if not video.get('user'):
            return []
            
        # For now, we'll just get videos by the same user
        related = self.get_videos(user=video['user'])
        
        # Filter out the current video and limit the results
        related = [v for v in related if v['id'] != video['id']][:limit]
        
        return related
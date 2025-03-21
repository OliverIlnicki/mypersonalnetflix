"""
Module for processing videos from different sources and creating previews.
"""
import os
import sys
import json
import logging
from typing import Optional, List, Dict, Any

from src.youtube_source import YouTubeSource
from src.local_source import LocalFileSource
from src.db_helper import DatabaseHelper
from src.create_preview import VideoPreviewCreator

# Set up logging
logger = logging.getLogger(__name__)

class VideoProcessor:
    """
    Main class that handles processing of videos from different sources
    """
    def __init__(self, output_dir: str, db_path: Optional[str] = None):
        self.output_dir = output_dir
        self.db_path = db_path or os.path.join(output_dir, "videos.db")
        self.video_sources = {}
        
        # Ensure base directories exist
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")
        
        # Initialize database
        self.db_helper = DatabaseHelper(self.db_path)
        
        # Initialize preview creator
        self.preview_creator = VideoPreviewCreator()
        
        # Register available video sources
        self.register_source("youtube", YouTubeSource())
        self.register_source("local", LocalFileSource())
    
    def register_source(self, name: str, source) -> None:
        """
        Register a new video source
        """
        self.video_sources[name] = source
        logger.info(f"Registered video source: {name}")
    
    def ensure_user_directories(self, username: str) -> Dict[str, str]:
        """
        Create user-specific directories and return paths
        """
        # Main user directory
        user_dir = os.path.join(self.output_dir, username)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
            logger.info(f"Created user directory: {user_dir}")
        
        # Temporary videos directory
        temp_dir = os.path.join(user_dir, "temp_videos")
        if not os.path.exists(temp_dir):
            os.makedirs(temp_dir)
            
        # Thumbnails directory
        thumbnails_dir = os.path.join(user_dir, "thumbnails")
        if not os.path.exists(thumbnails_dir):
            os.makedirs(thumbnails_dir)
            logger.info(f"Created thumbnails directory: {thumbnails_dir}")
            
        # GIF directory
        gif_dir = os.path.join(user_dir, "previews")
        if not os.path.exists(gif_dir):
            os.makedirs(gif_dir)
            logger.info(f"Created GIF previews directory: {gif_dir}")
            
        return {
            "user_dir": user_dir,
            "temp_dir": temp_dir,
            "thumbnails_dir": thumbnails_dir,
            "gif_dir": gif_dir
        }
    
    def is_duplicate(self, url: str, content_hash: str) -> bool:
        """
        Check if a video is already in the database by URL or content hash
        """
        return self.db_helper.is_duplicate(url, content_hash)
    
    def process_url(self, url: str, username: str = "") -> Optional[Dict[str, Any]]:
        """
        Process a single URL and create a GIF preview
        """
        if not username:
            logger.error("Username is required for processing videos")
            return None
            
        # Create user directories
        user_paths = self.ensure_user_directories(username)
        
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
        video_path, thumbnail_path, video_title, video_description, upload_year = source.download_video(
            url, user_paths["temp_dir"]
        )
        
        if not video_path:
            logger.error(f"Failed to download video from {url}")
            return None
        
        # Generate content hash for duplicate detection
        content_hash = source.generate_content_hash(video_path)
        
        # Check for duplicates
        if self.is_duplicate(url, content_hash):
            # Clean up the downloaded files
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
            except Exception as e:
                logger.warning(f"Error cleaning up files for duplicate: {str(e)}")
                
            return None
        
        # Create preview files
        # First try to create an MP4 preview (much smaller file size)
        mp4_path = self.preview_creator.create_mp4_preview(
            video_path, 
            user_paths["gif_dir"],
            duration=8
        )
        
        # Also create a GIF preview as fallback (smaller duration to reduce file size)
        gif_path = self.preview_creator.create_gif_preview(
            video_path, 
            user_paths["gif_dir"],
            duration=5
        )
        
        # Move thumbnail to thumbnails directory
        if thumbnail_path:
            thumbnail_filename = os.path.basename(thumbnail_path)
            new_thumbnail_path = os.path.join(user_paths["thumbnails_dir"], thumbnail_filename)
            os.rename(thumbnail_path, new_thumbnail_path)
            thumbnail_path = new_thumbnail_path
        
        # Attempt to clean up the video file to save space
        try:
            # For local files, we may have created a symlink, so check if it's a link first
            if source_name != "local" or not os.path.islink(video_path):
                os.remove(video_path)
        except Exception as e:
            logger.warning(f"Could not remove temporary video file {video_path}: {str(e)}")
        
        # Use either MP4 or GIF path, preferring MP4 if available
        preview_path = mp4_path if mp4_path else gif_path
        
        if preview_path:
            # Create dictionary with all the information
            video_info = {
                "user": username,
                "url": url,
                "source": source_name,
                "title": video_title,
                "description": video_description,
                "thumb_path": os.path.relpath(thumbnail_path, self.output_dir) if thumbnail_path else "",
                "vid_preview_path": os.path.relpath(preview_path, self.output_dir),
                "upload_year": upload_year,
                "content_hash": content_hash,
                "preview_type": "mp4" if mp4_path else "gif"  # Store the preview type
            }
            
            # Save to database
            self.db_helper.save_to_database(video_info)
            
            return video_info
        
        return None
    
    def process_links_file(self, links_file: str, username: str = "") -> List[Dict[str, Any]]:
        """
        Process a file containing video links and create GIF previews
        """
        if not username:
            logger.error("Username is required for processing videos")
            return []
            
        results = []
        
        try:
            with open(links_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    url = line.strip()
                    if not url or not url.startswith(("http", "file://", "/")):
                        logger.warning(f"Line {line_num}: Invalid URL or path - {url}")
                        continue
                        
                    logger.info(f"Processing URL/path {line_num}: {url}")
                    
                    video_info = self.process_url(url, username)
                    if video_info:
                        results.append(video_info)
        
        except Exception as e:
            logger.error(f"Error processing links file: {str(e)}")
        
        # Try to clean up the temp directory if it's empty
        try:
            temp_dir = os.path.join(self.output_dir, username, "temp_videos")
            if len(os.listdir(temp_dir)) == 0:
                os.rmdir(temp_dir)
        except:
            pass
            
        return results
    
    def save_results(self, results: List[Dict[str, Any]], username: str) -> Dict[str, str]:
        """
        Save the results to JSON file
        """
        user_dir = os.path.join(self.output_dir, username)
        
        # Save as JSON (human-readable and portable)
        json_path = os.path.join(user_dir, "video_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved results as JSON to {json_path}")
        
        return {"json_path": json_path}
    
    def process_local_directory(self, directory: str, username: str) -> List[Dict[str, Any]]:
        """
        Process all video files in a directory
        """
        if not os.path.isdir(directory):
            logger.error(f"'{directory}' is not a valid directory")
            return []
        
        # Find all video files in the directory
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
        video_files = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(video_files)} video files in directory")
        
        # Process each video file
        results = []
        for video_file in video_files:
            video_info = self.process_url(video_file, username)
            if video_info:
                results.append(video_info)
                
        return results
    
    def query_database(self, user: Optional[str] = None, year: Optional[int] = None, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query the database with optional filters
        """
        return self.db_helper.query_database(user, year, source)
    
    def close(self) -> None:
        """
        Close database connection
        """
        self.db_helper.close()
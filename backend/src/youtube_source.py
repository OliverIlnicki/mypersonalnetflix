"""
YouTube Video Source Module
==========================

This module implements the VideoSource interface for YouTube videos,
enabling the Video Preview Application to download and process videos
from YouTube.

Features:
- YouTube URL validation and accessibility checking
- Video downloading using pytubefix
- Thumbnail downloading
- Metadata extraction (title, description, upload year)
"""
import os
import sys
import logging
from pytubefix import YouTube
from typing import Optional, Tuple, Dict, List, Any

# Fix import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from .base_source import VideoSource
from .youtube_url_checker import check_youtube_video_accessible

# Set up logging
logger = logging.getLogger(__name__)

class YouTubeSource(VideoSource):
    """
    Implementation for downloading and processing YouTube videos.
    
    This class handles:
    - YouTube URL validation
    - Video downloading in appropriate resolution
    - Thumbnail retrieval
    - Metadata extraction
    """
    
    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is a valid and accessible YouTube URL.
        
        This method uses the youtube_url_checker to verify both
        the URL format and video accessibility.
        
        Args:
            url: YouTube URL to check
            
        Returns:
            bool: True if the URL is a valid and accessible YouTube video
        """
        is_valid, message = check_youtube_video_accessible(url)
        if not is_valid:
            logger.warning(f"Invalid YouTube URL: {url} - {message}")
        return is_valid

    def download_video(self, url: str, output_dir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Download a YouTube video in low resolution and extract metadata.
        
        This method:
        1. Extracts video metadata (title, description, upload year)
        2. Downloads the video in an appropriate resolution
        3. Downloads the thumbnail image
        
        Args:
            url: YouTube URL
            output_dir: Directory where downloaded files will be saved
            
        Returns:
            Tuple of (video_path, thumbnail_path, title, description, upload_year)
        """
        try:
            logger.info(f"Downloading YouTube video: {url}")
            
            yt = YouTube(url)
            # Get the title and description
            video_title = yt.title
            video_description = yt.description
            safe_title = "".join([c for c in video_title if c.isalnum() or c in ' .-']).strip()

            # Get the publish date and extract the year
            publish_date = yt.publish_date
            upload_year = publish_date.year if publish_date else None
            
            logger.info(f"Video info: {video_title} ({upload_year})")

            # Get the lowest resolution stream that has video (to save bandwidth)
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').first()
            if not stream:
                logger.error(f"No suitable stream found for {url}")
                return None, None, None, None, None

            # Download the video
            output_path = stream.download(output_path=output_dir, filename=f"{safe_title}.mp4")
            logger.info(f"Downloaded {url} to {output_path}")

            # Download the thumbnail
            thumbnail_url = yt.thumbnail_url
            thumbnail_path = os.path.join(output_dir, f"{safe_title}_thumbnail.jpg")
            thumbnail_result = self.download_thumbnail(thumbnail_url, thumbnail_path)
            
            if thumbnail_result:
                logger.info(f"Downloaded thumbnail to {thumbnail_path}")
            else:
                logger.warning(f"Failed to download thumbnail for {url}")

            return output_path, thumbnail_path, video_title, video_description, upload_year
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return None, None, None, None, None
"""
Video Source Abstract Base Class
===============================

This module defines the base interface for video sources in the Video Preview Application.
Different video sources (YouTube, local files, etc.) implement this interface to provide
a consistent way to download and process videos from various platforms.
"""
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, List, Any
import hashlib
import requests


class VideoSource(ABC):
    """
    Abstract base class for different video source platforms.
    
    This class defines the interface that all video sources must implement,
    plus some common utility methods that can be used by all implementations.
    """
    
    @abstractmethod
    def download_video(self, url: str, output_dir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Download a video from the source and return relevant information.
        
        Args:
            url: URL or path to the video
            output_dir: Directory where the downloaded files should be saved
            
        Returns:
            Tuple containing:
            - video_path: Path to downloaded video file
            - thumbnail_path: Path to downloaded thumbnail
            - title: Video title
            - description: Video description
            - upload_year: Year the video was uploaded
        """
        pass
    
    @abstractmethod
    def is_valid_url(self, url: str) -> bool:
        """
        Check if the URL is valid for this video source.
        
        Args:
            url: URL or path to check
            
        Returns:
            bool: True if the URL is valid for this source
        """
        pass
    
    @staticmethod
    def download_thumbnail(url: str, output_path: str) -> Optional[str]:
        """
        Download the thumbnail image from the given URL.
        
        This is a utility method that can be used by any source implementation.
        
        Args:
            url: URL of the thumbnail image
            output_path: Path where the thumbnail should be saved
            
        Returns:
            str: Path to the downloaded thumbnail or None if download failed
        """
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                return output_path
            else:
                return None
        except Exception as e:
            return None
    
    @staticmethod
    def generate_content_hash(video_path: str) -> str:
        """
        Generate a hash of the first 1MB of the video file to identify duplicates.
        
        The hash is used to identify duplicate videos even if they come from
        different sources or have different URLs.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            str: MD5 hash of the first 1MB of the video file
        """
        try:
            hasher = hashlib.md5()
            with open(video_path, 'rb') as f:
                # Read only the first 1MB for efficiency
                chunk = f.read(1024 * 1024)
                hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            return ""
"""
YouTube URL Checker Module
=========================

This module provides utilities for validating YouTube URLs and checking
if videos are accessible. Since the standard pytube library has issues with
some YouTube features, this module uses pytubefix as a more reliable alternative.

The module handles various YouTube URL formats and detects common accessibility
issues like private videos, age restrictions, and content violations.
"""
import re
import logging
import requests
from pytubefix import YouTube
from pytubefix.exceptions import VideoUnavailable, VideoPrivate, LiveStreamError
from typing import Tuple

# Set up logging
logger = logging.getLogger(__name__)

def is_valid_youtube_url(url: str) -> bool:
    """
    Check if the URL matches YouTube's pattern.
    
    This function validates the URL format without making network requests,
    using regex patterns to match standard YouTube URL formats.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if the URL matches YouTube's format
    """
    patterns = [
        r"^(https?\:\/\/)?(www\.)?(youtube\.com\/watch\?v=)[\w-]{11}.*",
        r"^(https?\:\/\/)?(youtu\.be\/)[\w-]{11}.*"
    ]
    return any(re.match(pattern, url) for pattern in patterns)

def check_youtube_video_accessible(url: str) -> Tuple[bool, str]:
    """
    Check if a YouTube video is accessible.
    
    This function performs a multi-step validation:
    1. Validates the URL format
    2. Performs a HEAD request to check if the URL is valid
    3. Uses pytubefix to check availability, age restrictions, etc.
    
    Args:
        url: YouTube URL to check
        
    Returns:
        Tuple containing:
        - bool: True if the video is accessible, False otherwise
        - str: Message with details about accessibility
    """
    if not is_valid_youtube_url(url):
        logger.warning(f"Invalid YouTube URL format: {url}")
        return False, "Invalid YouTube URL format"
    
    try:
        # First check with HEAD request to quickly validate URL
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code != 200:
            logger.warning(f"HTTP Error {response.status_code} for URL: {url}")
            return False, f"HTTP Error {response.status_code}"
        
        # Then check with pytubefix for detailed validation
        yt = YouTube(url)
        yt.check_availability()
        
        # Additional check for age restriction by trying to get title
        _ = yt.title  # This might fail for age-restricted content
        
        logger.info(f"YouTube video is accessible: {url}")
        return True, "Video is accessible"
    
    except requests.exceptions.RequestException as e:
        logger.warning(f"Connection failed for URL {url}: {str(e)}")
        return False, f"Connection failed: {str(e)}"
    
    except VideoUnavailable:
        logger.warning(f"Video unavailable (deleted or private): {url}")
        return False, "Video unavailable (deleted or private)"
    
    except VideoPrivate:
        logger.warning(f"Video is private: {url}")
        return False, "Video is private"
    
    except LiveStreamError:
        logger.warning(f"Live stream is not accessible: {url}")
        return False, "Live stream is not accessible"
    
    except Exception as e:
        error_msg = str(e).lower()
        if 'age restricted' in error_msg:
            logger.warning(f"Age-restricted content: {url}")
            return False, "Age-restricted content (login required)"
        if 'content check' in error_msg:
            logger.warning(f"Content violation restriction: {url}")
            return False, "Content violation restriction"
        
        logger.warning(f"Error accessing video {url}: {str(e)}")
        return False, f"Error accessing video: {str(e)}"

if __name__ == "__main__":
    # This can be used as a simple CLI if needed
    import sys
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result, message = check_youtube_video_accessible(url)
        print(f"Result: {'Accessible' if result else 'Not accessible'}")
        print(f"Message: {message}")
    else:
        print("Please provide a YouTube URL as an argument.")
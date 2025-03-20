"""
YouTube URL Checker. Pytube is broken, therefore pytubefix is used.
"""
import re
import requests
from pytubefix import YouTube
from pytubefix.exceptions import VideoUnavailable, VideoPrivate, LiveStreamError

def is_valid_youtube_url(url: str) -> bool:
    """Check if the URL matches YouTube's pattern. At the moment not needed, but useful for later optimization."""
    patterns = [
        r"^(https?\:\/\/)?(www\.)?(youtube\.com\/watch\?v=)[\w-]{11}.*",
        r"^(https?\:\/\/)?(youtu\.be\/)[\w-]{11}.*"
    ]
    return any(re.match(pattern, url) for pattern in patterns)

def check_youtube_video_accessible(url: str) -> tuple[bool, str]:
    """
    Check if a YouTube video is accessible.
    Returns (True, "Video is accessible") if accessible,
    (False, error_message) otherwise.
    """
    if not is_valid_youtube_url(url):
        return False, "Invalid YouTube URL format"
    
    try:
        # First check with HEAD request
        response = requests.head(url, timeout=10, allow_redirects=True)
        if response.status_code != 200:
            return False, f"HTTP Error {response.status_code}"
        
        # Then check with pytubefix for detailed validation
        yt = YouTube(url)
        yt.check_availability()
        
        # Additional check for age restriction by trying to get title
        _ = yt.title  # This might fail for age-restricted content
        
        return True, "Video is accessible"
    
    except requests.exceptions.RequestException as e:
        return False, f"Connection failed: {str(e)}"
    
    except VideoUnavailable:
        return False, "Video unavailable (deleted or private)"
    
    except VideoPrivate:
        return False, "Video is private"
    
    except LiveStreamError:
        return False, "Live stream is not accessible"
    
    except Exception as e:
        error_msg = str(e).lower()
        if 'age restricted' in error_msg:
            return False, "Age-restricted content (login required)"
        if 'content check' in error_msg:
            return False, "Content violation restriction"
        return False, f"Error accessing video: {str(e)}"

if __name__ == "__main__":
    # This can be used as a simple CLI if needed
    import sys
    if len(sys.argv) > 1:
        url = sys.argv[1]
        result, message = check_youtube_video_accessible(url)
        print(f"Result: {'Accessible' if result else 'Not accessible'}")
        print(f"Message: {message}")
    else:
        print("Please provide a YouTube URL as an argument.")
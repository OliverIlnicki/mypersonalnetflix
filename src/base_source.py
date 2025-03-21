from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, List, Any
import hashlib
#from videos2db import logger
import requests
class VideoSource(ABC):
    """
    Abstract base class for different video source platforms
    """
    @abstractmethod
    def download_video(self, url: str, output_dir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Download a video from the source and return relevant information
        
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
        Check if the URL is valid for this video source
        """
        pass
    
    @staticmethod
    def download_thumbnail(url: str, output_path: str) -> Optional[str]:
        """
        Download the thumbnail image from the given URL
        """
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                #logger.info(f"Downloaded thumbnail to {output_path}")
                return output_path
            else:
                #logger.error(f"Failed to download thumbnail. Status code: {response.status_code}")
                return None
        except Exception as e:
            #logger.error(f"Error downloading thumbnail: {str(e)}")
            return None
    
    @staticmethod
    def generate_content_hash(video_path: str) -> str:
        """
        Generate a hash of the first 1MB of the video file to identify duplicates
        """
        try:
            hasher = hashlib.md5()
            with open(video_path, 'rb') as f:
                # Read only the first 1MB for efficiency
                chunk = f.read(1024 * 1024)
                hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            #logger.error(f"Error generating content hash: {str(e)}")
            return ""

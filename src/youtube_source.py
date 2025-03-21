#%%

import os
import pytubefix
from pytubefix import YouTube
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import moviepy.video.VideoClip
from src.base_source import VideoSource
from src.youtube_url_checker import  check_youtube_video_accessible
#from videos2db import logger
# Set up logging
from typing import Optional, Tuple, Dict, List, Any
#%%
class YouTubeSource(VideoSource):
    """
    Implementation for YouTube videos
    """
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        return check_youtube_video_accessible(url)[0]

    def download_video(self, url: str, output_dir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Download a YouTube video in low resolution and extract metadata
        """
        try:
            yt = YouTube(url)
            # Get the title and description
            video_title = yt.title
            video_description = yt.description
            safe_title = "".join([c for c in video_title if c.isalnum() or c in ' .-']).strip()

            # Get the publish date and extract the year
            publish_date = yt.publish_date
            upload_year = publish_date.year if publish_date else None

            # Get the lowest resolution stream that has video
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').first()
            if not stream:
              #  logger.error(f"No suitable stream found for {url}")
                return None, None, None, None, None

            # Download the video
            output_path = stream.download(output_path=output_dir, filename=f"{safe_title}.mp4")
            #logger.info(f"Downloaded {url} to {output_path}")

            # Download the thumbnail
            thumbnail_url = yt.thumbnail_url
            thumbnail_path = os.path.join(output_dir, f"{safe_title}_thumbnail.jpg")
            self.download_thumbnail(thumbnail_url, thumbnail_path)

            return output_path, thumbnail_path, video_title, video_description, upload_year
        except Exception as e:
            #logger.error(f"Error downloading {url}: {str(e)}")
            return None, None, None, None, None
# %%
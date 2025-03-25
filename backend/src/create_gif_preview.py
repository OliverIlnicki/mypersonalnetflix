"""
GIF Preview Generator
====================

This module creates optimized GIF previews from video files for the Video Preview Application.
It selects a representative portion of the video, avoiding intros and outros, and
converts it to a GIF format suitable for preview display.
"""
import os
import random
import logging
from moviepy.video.io import VideoFileClip
from typing import Optional

# Set up logging
logger = logging.getLogger(__name__)

def create_gif_preview(video_path: str, output_dir: str, duration: int = 30) -> Optional[str]:
    """
    Create a GIF preview from a representative part of the video.
    
    This function:
    1. Loads the video file
    2. Selects a portion from the middle (avoiding intros/outros)
    3. Resizes to a smaller resolution
    4. Converts to GIF format
    
    Args:
        video_path: Path to the source video file
        output_dir: Directory to save the GIF preview
        duration: Target duration of the GIF in seconds (default 30s)
        
    Returns:
        str: Path to the created GIF preview, or None if creation failed
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
        
        # Select start point and duration based on video length
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
        gif_path = os.path.join(output_dir, gif_filename)
        
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
            try:
                clip.close()
            except:
                pass
        return None
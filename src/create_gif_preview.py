import os
import random
from moviepy.video.io import VideoFileClip
from typing import Optional, Tuple, Dict, List, Any

def create_gif_preview(self, video_path: str, duration: int = 30) -> Optional[str]:
        """
        Create a GIF preview from a representative part of the video
        """
        try:
            if not os.path.exists(video_path):
                #logger.error(f"Video file not found: {video_path}")
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
            
           # logger.info(f"Created GIF preview: {gif_path}")
            return gif_path
        except Exception as e:
            #logger.error(f"Error creating GIF: {str(e)}")
            if 'clip' in locals():
                clip.close()
            return None
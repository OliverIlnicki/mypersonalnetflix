"""
Module for creating optimized preview videos from video files.
Uses moviepy instead of ffprobe for compatibility.
"""
import os
import random
import logging
import subprocess
from typing import Optional, Tuple
from moviepy.video.io.VideoFileClip import VideoFileClip

# Set up logging
logger = logging.getLogger(__name__)

class VideoPreviewCreator:
    """
    Class that handles creation of optimized video previews
    """
    def __init__(self):
        """Initialize the preview creator"""
        pass
        
    def create_gif_preview(self, video_path: str, output_dir: str, duration: int = 5) -> Optional[str]:
        """
        Create a highly optimized GIF preview from a representative part of the video
        
        Args:
            video_path: Path to the source video file
            output_dir: Directory to save the GIF preview
            duration: Target duration of the GIF in seconds (default 5s for smaller file size)
            
        Returns:
            Path to the created GIF preview, or None if creation failed
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None
                
            # Get video duration and select start time
            start_time, actual_duration = self._get_clip_timing_moviepy(video_path, duration)
            if start_time is None:
                return None
                
            # Get the base filename without extension
            video_filename = os.path.basename(video_path)
            base_name = os.path.splitext(video_filename)[0]
            gif_filename = f"{base_name}.gif"
            gif_path = os.path.join(output_dir, gif_filename)
            
            # Load the clip
            clip = VideoFileClip(video_path)
            
            try:
                # Extract the subclip
                subclip = clip.subclip(start_time, start_time + actual_duration)
                
                # Resize to lower resolution for GIF (240px width)
                resized_clip = subclip.resize(width=240)
                
                # Write the GIF with reduced framerate for smaller file size
                resized_clip.write_gif(gif_path, fps=8, opt="OptimizeTransparency")
                
                # Close the clips to free resources
                resized_clip.close()
                subclip.close()
                clip.close()
                
                logger.info(f"Created GIF preview: {gif_path}")
                return gif_path
            except Exception as e:
                logger.error(f"Error creating GIF: {str(e)}")
                # Try a fallback method
                clip.close()
                return self._create_fallback_gif(video_path, gif_path, start_time, actual_duration)
                
        except Exception as e:
            logger.error(f"Error creating GIF: {str(e)}")
            return None
    
    def _create_fallback_gif(self, video_path: str, gif_path: str, start_time: float, duration: float) -> Optional[str]:
        """Simple fallback method if other methods fail"""
        try:
            clip = VideoFileClip(video_path)
            
            # If subclip fails, just use the first few seconds
            if start_time > 0:
                try:
                    subclip = clip.subclip(0, min(5.0, clip.duration))
                except:
                    subclip = clip
            else:
                subclip = clip
                
            # Write the GIF with minimal settings
            subclip.write_gif(gif_path, fps=5)
            
            # Close the clips
            subclip.close()
            clip.close()
            
            logger.info(f"Created fallback GIF preview: {gif_path}")
            return gif_path
        except Exception as e:
            logger.error(f"Error creating fallback GIF: {str(e)}")
            return None
    
    def create_mp4_preview(self, video_path: str, output_dir: str, duration: int = 8) -> Optional[str]:
        """
        Create a tiny MP4 preview that can be used as an alternative to GIF
        Using subprocess to call ffmpeg directly if available, otherwise falls back to moviepy
        
        Args:
            video_path: Path to the source video file
            output_dir: Directory to save the MP4 preview
            duration: Target duration in seconds
            
        Returns:
            Path to the created MP4 preview, or None if creation failed
        """
        try:
            if not os.path.exists(video_path):
                logger.error(f"Video file not found: {video_path}")
                return None
                
            # Get video duration and select start time
            start_time, actual_duration = self._get_clip_timing_moviepy(video_path, duration)
            if start_time is None:
                return None
                
            # Get the base filename without extension
            video_filename = os.path.basename(video_path)
            base_name = os.path.splitext(video_filename)[0]
            mp4_filename = f"{base_name}_preview.mp4"
            mp4_path = os.path.join(output_dir, mp4_filename)
            
            # Try using ffmpeg directly if available
            try:
                mp4_cmd = [
                    "ffmpeg", "-y",
                    "-ss", str(start_time),
                    "-t", str(actual_duration),
                    "-i", video_path,
                    "-vf", "scale=320:-1",
                    "-c:v", "libx264",
                    "-crf", "28",
                    "-preset", "medium",
                    "-an",
                    "-pix_fmt", "yuv420p",
                    mp4_path
                ]
                
                result = subprocess.run(mp4_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                if result.returncode == 0:
                    logger.info(f"Created MP4 preview using ffmpeg: {mp4_path}")
                    return mp4_path
                else:
                    logger.warning(f"ffmpeg failed, falling back to moviepy: {result.stderr.decode()}")
                    # Fall back to moviepy if ffmpeg command fails
            except (FileNotFoundError, subprocess.SubprocessError) as e:
                logger.warning(f"ffmpeg not available or failed, falling back to moviepy: {str(e)}")
                # Continue with moviepy fallback
                
            # Fallback: Use moviepy to create MP4
            clip = VideoFileClip(video_path)
            subclip = clip.subclip(start_time, start_time + actual_duration)
            
            # Resize to lower resolution
            resized_clip = subclip.resize(width=320)
            
            # Remove audio
            final_clip = resized_clip.without_audio()
            
            # Write the MP4 file
            final_clip.write_videofile(
                mp4_path,
                codec='libx264',
                preset='medium',
                ffmpeg_params=['-crf', '28', '-pix_fmt', 'yuv420p'],
                fps=24,
                logger=None  # Suppress moviepy's verbose output
            )
            
            # Close the clips
            final_clip.close()
            resized_clip.close()
            subclip.close()
            clip.close()
            
            logger.info(f"Created MP4 preview using moviepy: {mp4_path}")
            return mp4_path
        except Exception as e:
            logger.error(f"Error creating MP4 preview: {str(e)}")
            return None
    
    def _get_clip_timing_moviepy(self, video_path: str, target_duration: int) -> Tuple[Optional[float], Optional[float]]:
        """
        Get the start time and actual duration for the preview clip using MoviePy
        
        Args:
            video_path: Path to the video file
            target_duration: Desired duration in seconds
            
        Returns:
            Tuple of (start_time, actual_duration)
        """
        try:
            # Use MoviePy to get video duration
            clip = VideoFileClip(video_path)
            video_duration = clip.duration
            
            # Skip the first and last 20% of the video to avoid intros and outros
            start_threshold = video_duration * 0.2
            end_threshold = video_duration * 0.8
            
            # Select a start point in the middle 60% of the video
            if video_duration <= target_duration:
                # If video is shorter than desired duration, use the whole video
                start_time = 0
                actual_duration = video_duration
            else:
                # Make sure we don't go beyond the end of the video
                max_start = min(end_threshold - target_duration, video_duration - target_duration)
                min_start = max(start_threshold, 0)
                
                if max_start <= min_start:
                    start_time = 0
                else:
                    start_time = random.uniform(min_start, max_start)
                    
                actual_duration = min(target_duration, video_duration - start_time)
            
            clip.close()
            return start_time, actual_duration
            
        except Exception as e:
            logger.error(f"Error determining clip timing: {str(e)}")
            return None, None
            
    def extract_thumbnail(self, video_path: str, output_path: str, time_percent: float = 0.3) -> bool:
        """
        Extract a thumbnail from the video at the specified position
        
        Args:
            video_path: Path to the source video file
            output_path: Where to save the thumbnail
            time_percent: Position in the video as a percentage (0.0 to 1.0)
            
        Returns:
            True if thumbnail was successfully created, False otherwise
        """
        try:
            clip = VideoFileClip(video_path)
            thumbnail_time = clip.duration * time_percent
            
            # Save a frame as the thumbnail
            clip.save_frame(output_path, t=thumbnail_time)
            
            clip.close()
            logger.info(f"Created thumbnail at {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {str(e)}")
            return False
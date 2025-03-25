"""
Local Video Source Module
========================

This module implements the VideoSource interface for local video files,
enabling the Video Preview Application to process videos stored on the 
local file system.

Features:
- Detection and validation of local video files
- Metadata extraction from accompanying text files
- Thumbnail generation
- Content hash generation for duplicate detection
"""
import os
import sys
import logging
from datetime import datetime
from moviepy.video.io import VideoFileClip
from typing import Optional, Tuple, Dict, List, Any

# Fix import paths
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from .base_source import VideoSource

# Set up logging
logger = logging.getLogger(__name__)

class LocalFileSource(VideoSource):
    """
    Implementation for processing local video files with description text files.
    
    This class handles:
    - Validation of local video file paths
    - Metadata extraction from accompanying text files
    - Symlink or copy operations for organizing videos
    - Thumbnail creation from video frames
    """
    
    def is_valid_url(self, url: str) -> bool:
        """
        Check if URL is a path to a local video file.
        
        For local files, the "URL" is actually a file path that can be:
        - An absolute path
        - A relative path
        - A file:// URL
        
        Args:
            url: Path to check
            
        Returns:
            bool: True if the path points to a valid video file
        """
        return (url.startswith("file://") or 
                os.path.exists(url) and 
                any(url.lower().endswith(ext) for ext in 
                    ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']))
    
    def download_video(self, url: str, output_dir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Process a local video file and extract metadata from an accompanying description file.
        
        This method:
        1. Locates the video file and checks for a description file
        2. Extracts metadata (title, description, year)
        3. Creates a symlink or copy in the output directory
        4. Generates a thumbnail
        
        Args:
            url: Path to the local video file
            output_dir: Directory where processed files will be saved
            
        Returns:
            Tuple of (video_path, thumbnail_path, title, description, upload_year)
        """
        try:
            # Normalize the file path (remove file:// prefix if present)
            file_path = url.replace("file://", "") if url.startswith("file://") else url
            
            if not os.path.exists(file_path):
                logger.error(f"Video file not found: {file_path}")
                return None, None, None, None, None
            
            # Get file and directory information
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            file_dir = os.path.dirname(file_path)
            
            # Look for description file with matching name
            description_file = os.path.join(file_dir, f"{base_name}.txt")
            description_text = ""
            upload_year = None
            
            # Extract metadata from description file if it exists
            if os.path.exists(description_file):
                with open(description_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    lines = content.split('\n')
                    
                    # First line is the title
                    video_title = lines[0] if lines else base_name
                    
                    # Process remaining lines
                    filtered_lines = []
                    for line in lines[1:]:  # Skip the first line (title)
                        if line.lower().startswith("year:"):
                            try:
                                year_text = line.split(":", 1)[1].strip()
                                upload_year = int(year_text)
                            except ValueError:
                                pass  # Ignore invalid year values
                        else:
                            filtered_lines.append(line)
                    
                    # Join remaining lines as description
                    description_text = '\n'.join(filtered_lines)
            else:
                # Use filename as title if no description file
                video_title = base_name
            
            # If no year was specified, use file modification time
            if not upload_year:
                file_mtime = os.path.getmtime(file_path)
                upload_year = datetime.fromtimestamp(file_mtime).year
            
            # Create safe filename for output
            safe_title = "".join([c for c in video_title if c.isalnum() or c in ' ._-']).strip()
            output_file_path = os.path.join(output_dir, f"{safe_title}.mp4")
            
            # Create a symlink or copy the file to the output directory
            if os.path.exists(output_file_path) and not os.path.samefile(file_path, output_file_path):
                try:
                    os.remove(output_file_path)
                except:
                    logger.warning(f"Could not remove existing file: {output_file_path}")
                
            # Try to use symlink if available (saves disk space)
            if hasattr(os, 'symlink'):
                try:
                    os.symlink(os.path.abspath(file_path), output_file_path)
                    logger.info(f"Created symlink to video file at {output_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to create symlink, copying file instead: {str(e)}")
                    with open(file_path, 'rb') as src, open(output_file_path, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"Copied video file to {output_file_path}")
            else:
                # Fall back to copying the file
                with open(file_path, 'rb') as src, open(output_file_path, 'wb') as dst:
                    dst.write(src.read())
                logger.info(f"Copied video file to {output_file_path}")
            
            # Create a thumbnail from an early frame
            thumbnail_path = os.path.join(output_dir, f"{safe_title}_thumbnail.jpg")
            try:
                clip = VideoFileClip(file_path)
                thumbnail_time = clip.duration * 0.1  # 10% into the video
                clip.save_frame(thumbnail_path, t=thumbnail_time)
                clip.close()
                logger.info(f"Created thumbnail at {thumbnail_path}")
            except Exception as e:
                logger.error(f"Error creating thumbnail: {str(e)}")
                thumbnail_path = None
            
            return output_file_path, thumbnail_path, video_title, description_text, upload_year
        except Exception as e:
            logger.error(f"Error processing local video file: {str(e)}")
            return None, None, None, None, None
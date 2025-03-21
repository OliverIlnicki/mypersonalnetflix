import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime
from src.base_source import VideoSource
#from videos2db import logger
from typing import Optional, Tuple, Dict, List, Any

from moviepy.video.io import VideoFileClip

class LocalFileSource(VideoSource):
    """
    Implementation for local video files with description text files
    """
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a path to a local video file"""
        # For local files, the URL is actually a file path
        return (url.startswith("file://") or 
                os.path.exists(url) and 
                any(url.lower().endswith(ext) for ext in 
                    ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']))
    
    def download_video(self, url: str, output_dir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
    Process a local video file and extract metadata from an accompanying description file
    """
        try:
            file_path = url.replace("file://", "") if url.startswith("file://") else url
            
            if not os.path.exists(file_path):
                return None, None, None, None, None
            
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            file_dir = os.path.dirname(file_path)
            
            description_file = os.path.join(file_dir, f"{base_name}.txt")
            description_text = ""
            upload_year = None
            
            if os.path.exists(description_file):
                with open(description_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    lines = content.split('\n')
                    
                    video_title = lines[0] if lines else base_name
                    
                    filtered_lines = []
                    for line in lines[1:]:  # Skip the first line (title)
                        if line.lower().startswith("year:"):
                            try:
                                year_text = line.split(":", 1)[1].strip()
                                upload_year = int(year_text)
                            except ValueError:
                                pass  # Falls die Jahreszahl ungültig ist, ignorieren
                        else:
                            filtered_lines.append(line)
                    
                    description_text = '\n'.join(filtered_lines)
            else:
                video_title = base_name
            
            if not upload_year:
                file_mtime = os.path.getmtime(file_path)
                upload_year = datetime.fromtimestamp(file_mtime).year
            
            safe_title = "".join([c for c in video_title if c.isalnum() or c in ' ._-']).strip()
            output_file_path = os.path.join(output_dir, f"{safe_title}.mp4")
            
            if hasattr(os, 'symlink'):
                try:
                    if os.path.exists(output_file_path):
                        os.remove(output_file_path)
                    os.symlink(os.path.abspath(file_path), output_file_path)
                except Exception:
                    with open(file_path, 'rb') as src, open(output_file_path, 'wb') as dst:
                        dst.write(src.read())
            else:
                with open(file_path, 'rb') as src, open(output_file_path, 'wb') as dst:
                    dst.write(src.read())
            
            thumbnail_path = os.path.join(output_dir, f"{safe_title}_thumbnail.jpg")
            try:
                clip = VideoFileClip(file_path)
                thumbnail_time = clip.duration * 0.1
                clip.save_frame(thumbnail_path, t=thumbnail_time)
                clip.close()
            except Exception:
                thumbnail_path = None
            
            return output_file_path, thumbnail_path, video_title, description_text, upload_year
        except Exception:
            return None, None, None, None, None

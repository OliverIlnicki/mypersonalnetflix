#%%
import os
import sys
import random
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import argparse
import logging
import requests
import pickle
import hashlib
from abc import ABC, abstractmethod
from typing import Optional, Tuple, Dict, List, Any
#%%
# External dependencies
import pytube
from pytube import YouTube
import moviepy.video.VideoClip
#%%
# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
#%%
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
                logger.info(f"Downloaded thumbnail to {output_path}")
                return output_path
            else:
                logger.error(f"Failed to download thumbnail. Status code: {response.status_code}")
                return None
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {str(e)}")
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
            logger.error(f"Error generating content hash: {str(e)}")
            return ""

#%%
class YouTubeSource(VideoSource):
    """
    Implementation for YouTube videos
    """
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is a valid YouTube URL"""
        return "youtube.com" in url or "youtu.be" in url
    
    def download_video(self, url: str, output_dir: str) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], Optional[int]]:
        """
        Download a YouTube video in low resolution and extract metadata
        """
        try:
            yt = YouTube(url)
            # Get the title and description
            video_title = yt.title
            video_description = yt.description
            safe_title = "".join([c for c in video_title if c.isalnum() or c in ' ._-']).strip()
            
            # Get the publish date and extract the year
            publish_date = yt.publish_date
            upload_year = publish_date.year if publish_date else None
            
            # Get the lowest resolution stream that has video
            stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').first()
            if not stream:
                logger.error(f"No suitable stream found for {url}")
                return None, None, None, None, None
                
            # Download the video
            output_path = stream.download(output_path=output_dir, filename=f"{safe_title}.mp4")
            logger.info(f"Downloaded {url} to {output_path}")
            
            # Download the thumbnail
            thumbnail_url = yt.thumbnail_url
            thumbnail_path = os.path.join(output_dir, f"{safe_title}_thumbnail.jpg")
            self.download_thumbnail(thumbnail_url, thumbnail_path)
            
            return output_path, thumbnail_path, video_title, video_description, upload_year
        except Exception as e:
            logger.error(f"Error downloading {url}: {str(e)}")
            return None, None, None, None, None

#%%
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
            # Extract actual path if using file:// protocol
            file_path = url.replace("file://", "") if url.startswith("file://") else url
            
            if not os.path.exists(file_path):
                logger.error(f"Local file not found: {file_path}")
                return None, None, None, None, None
            
            # Extract information from the file
            file_name = os.path.basename(file_path)
            base_name = os.path.splitext(file_name)[0]
            file_dir = os.path.dirname(file_path)
            
            # Look for a description file with the same base name
            description_file = os.path.join(file_dir, f"{base_name}.txt")
            description_text = ""
            upload_year = None
            
            # Try to extract video title and description from text file
            if os.path.exists(description_file):
                with open(description_file, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read().strip()
                    lines = content.split('\n')
                    
                    # First line is title
                    video_title = lines[0] if lines else base_name
                    
                    # Rest is description
                    if len(lines) > 1:
                        description_text = '\n'.join(lines[1:])
                    
                    # Try to extract year from the description
                    for line in lines:
                        if line.lower().startswith("year:"):
                            try:
                                year_text = line.split(":", 1)[1].strip()
                                upload_year = int(year_text)
                                break
                            except:
                                pass
            else:
                # If no description file, use the base filename as the title
                video_title = base_name
            
            # If no upload year was found, try to use file modification date
            if not upload_year:
                file_mtime = os.path.getmtime(file_path)
                upload_year = datetime.fromtimestamp(file_mtime).year
            
            # Create a safe filename for copying
            safe_title = "".join([c for c in video_title if c.isalnum() or c in ' ._-']).strip()
            
            # Copy or link the video file to the temp directory
            output_file_path = os.path.join(output_dir, f"{safe_title}.mp4")
            
            # Instead of copying the whole file, create a symlink if the platform supports it
            # or copy directly if symlinks aren't supported/desired
            if hasattr(os, 'symlink'):
                try:
                    # Create a symlink if possible to avoid duplicate storage
                    if os.path.exists(output_file_path):
                        os.remove(output_file_path)
                    os.symlink(os.path.abspath(file_path), output_file_path)
                    logger.info(f"Created symlink to local file at {output_file_path}")
                except Exception as e:
                    logger.warning(f"Failed to create symlink, copying file instead: {str(e)}")
                    with open(file_path, 'rb') as src, open(output_file_path, 'wb') as dst:
                        dst.write(src.read())
                    logger.info(f"Copied local file to {output_file_path}")
            else:
                # Copy the file if symlinks aren't supported
                with open(file_path, 'rb') as src, open(output_file_path, 'wb') as dst:
                    dst.write(src.read())
                logger.info(f"Copied local file to {output_file_path}")
            
            # Try to extract a thumbnail using moviepy
            thumbnail_path = os.path.join(output_dir, f"{safe_title}_thumbnail.jpg")
            try:
                clip = VideoFileClip(file_path)
                # Take a frame from 10% into the video
                thumbnail_time = clip.duration * 0.1
                clip.save_frame(thumbnail_path, t=thumbnail_time)
                clip.close()
                logger.info(f"Created thumbnail at {thumbnail_path}")
            except Exception as e:
                logger.warning(f"Failed to create thumbnail: {str(e)}")
                thumbnail_path = None
            
            return output_file_path, thumbnail_path, video_title, description_text, upload_year
        except Exception as e:
            logger.error(f"Error processing local file {url}: {str(e)}")
            return None, None, None, None, None

#%%
class VideoPreviewCreator:
    """
    Main class that handles creation of video previews
    """
    def __init__(self, output_dir: str, db_path: Optional[str] = None):
        self.output_dir = output_dir
        self.db_path = db_path or os.path.join(output_dir, "videos.db")
        self.db_conn = None
        self.video_sources = {}
        
        # Register available video sources
        self.register_source("youtube", YouTubeSource())
        self.register_source("local", LocalFileSource())
        
        # Ensure directories exist
        self._create_directories()
        
        # Initialize database
        self.init_database()
    
    def register_source(self, name: str, source: VideoSource) -> None:
        """
        Register a new video source
        """
        self.video_sources[name] = source
        logger.info(f"Registered video source: {name}")
    
    def _create_directories(self) -> None:
        """
        Create necessary directories
        """
        # Main output directory
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created output directory: {self.output_dir}")
        
        # Temporary videos directory
        self.temp_dir = os.path.join(self.output_dir, "temp_videos")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            
        # Thumbnails directory
        self.thumbnails_dir = os.path.join(self.output_dir, "thumbnails")
        if not os.path.exists(self.thumbnails_dir):
            os.makedirs(self.thumbnails_dir)
            logger.info(f"Created thumbnails directory: {self.thumbnails_dir}")
            
        # GIF directory
        self.gif_dir = os.path.join(self.output_dir, "previews")
        if not os.path.exists(self.gif_dir):
            os.makedirs(self.gif_dir)
            logger.info(f"Created GIF previews directory: {self.gif_dir}")
    
    def init_database(self) -> None:
        """
        Initialize SQLite database with the required schema
        """
        try:
            self.db_conn = sqlite3.connect(self.db_path)
            cursor = self.db_conn.cursor()
            
            # Create videos table
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS videos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user TEXT,
                url TEXT UNIQUE,
                source TEXT,
                title TEXT,
                description TEXT,
                thumb_path TEXT,
                vid_preview_path TEXT,
                upload_year INTEGER,
                content_hash TEXT,
                date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            # Add content_hash column if it doesn't exist (for upgrades)
            try:
                cursor.execute("SELECT content_hash FROM videos LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE videos ADD COLUMN content_hash TEXT")
                logger.info("Added content_hash column to database schema")
            
            # Create an index on content_hash for faster duplicate checking
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_content_hash ON videos (content_hash)")
            
            self.db_conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None
    
    def create_gif_preview(self, video_path: str, duration: int = 30) -> Optional[str]:
        """
        Create a GIF preview from a representative part of the video
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
            
            logger.info(f"Created GIF preview: {gif_path}")
            return gif_path
        except Exception as e:
            logger.error(f"Error creating GIF: {str(e)}")
            if 'clip' in locals():
                clip.close()
            return None
    
    def is_duplicate(self, url: str, content_hash: str) -> bool:
        """
        Check if a video is already in the database by URL or content hash
        """
        if not self.db_conn:
            return False
            
        try:
            cursor = self.db_conn.cursor()
            
            # First check URL (exact duplicate)
            cursor.execute("SELECT id FROM videos WHERE url = ?", (url,))
            if cursor.fetchone():
                logger.info(f"Skipping duplicate URL: {url}")
                return True
            
            # Then check content hash (same video from different source)
            if content_hash:
                cursor.execute("SELECT id, url FROM videos WHERE content_hash = ?", (content_hash,))
                result = cursor.fetchone()
                if result:
                    logger.info(f"Skipping duplicate content (hash: {content_hash}), already exists as URL: {result[1]}")
                    return True
            
            return False
        except Exception as e:
            logger.error(f"Error checking for duplicates: {str(e)}")
            return False
    
    def save_to_database(self, video_info: Dict[str, Any]) -> Optional[int]:
        """
        Save a video record to the SQLite database
        """
        if not self.db_conn:
            logger.error("Database connection not available")
            return None
            
        try:
            cursor = self.db_conn.cursor()
            cursor.execute('''
            INSERT OR REPLACE INTO videos 
            (user, url, source, title, description, thumb_path, vid_preview_path, upload_year, content_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_info['user'],
                video_info['url'],
                video_info['source'],
                video_info['title'],
                video_info['description'],
                video_info['thumb_path'],
                video_info['vid_preview_path'],
                video_info['upload_year'],
                video_info.get('content_hash', '')
            ))
            self.db_conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return None
    
    def process_url(self, url: str, username: str = "") -> Optional[Dict[str, Any]]:
        """
        Process a single URL and create a GIF preview
        """
        # Determine the appropriate video source
        source_name = None
        source = None
        
        for name, src in self.video_sources.items():
            if src.is_valid_url(url):
                source_name = name
                source = src
                break
        
        if not source:
            logger.error(f"No compatible video source found for URL: {url}")
            return None
        
        # Download the video and thumbnail, get metadata
        video_path, thumbnail_path, video_title, video_description, upload_year = source.download_video(url, self.temp_dir)
        if not video_path:
            logger.error(f"Failed to download video from {url}")
            return None
        
        # Generate content hash for duplicate detection
        content_hash = source.generate_content_hash(video_path)
        
        # Check for duplicates
        if self.is_duplicate(url, content_hash):
            # Clean up the downloaded files
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                if thumbnail_path and os.path.exists(thumbnail_path):
                    os.remove(thumbnail_path)
            except Exception as e:
                logger.warning(f"Error cleaning up files for duplicate: {str(e)}")
                
            return None
        
        # Create GIF preview
        gif_path = self.create_gif_preview(video_path)
        
        # Move thumbnail to thumbnails directory
        if thumbnail_path:
            thumbnail_filename = os.path.basename(thumbnail_path)
            new_thumbnail_path = os.path.join(self.thumbnails_dir, thumbnail_filename)
            os.rename(thumbnail_path, new_thumbnail_path)
            thumbnail_path = new_thumbnail_path
        
        # Attempt to clean up the video file to save space
        try:
            # For local files, we may have created a symlink, so check if it's a link first
            if source_name != "local" or not os.path.islink(video_path):
                os.remove(video_path)
        except Exception as e:
            logger.warning(f"Could not remove temporary video file {video_path}: {str(e)}")
        
        if gif_path:
            # Create dictionary with all the information
            video_info = {
                "user": username,
                "url": url,
                "source": source_name,
                "title": video_title,
                "description": video_description,
                "thumb_path": os.path.relpath(thumbnail_path, self.output_dir) if thumbnail_path else "",
                "vid_preview_path": os.path.relpath(gif_path, self.output_dir),
                "upload_year": upload_year,
                "content_hash": content_hash
            }
            
            # Save to database
            if self.db_conn:
                self.save_to_database(video_info)
            
            return video_info
        
        return None
    
    def process_links_file(self, links_file: str, username: str = "") -> List[Dict[str, Any]]:
        """
        Process a file containing video links and create GIF previews
        """
        results = []
        
        try:
            with open(links_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    url = line.strip()
                    if not url or not url.startswith(("http", "file://", "/")):
                        logger.warning(f"Line {line_num}: Invalid URL or path - {url}")
                        continue
                        
                    logger.info(f"Processing URL/path {line_num}: {url}")
                    
                    video_info = self.process_url(url, username)
                    if video_info:
                        results.append(video_info)
        
        except Exception as e:
            logger.error(f"Error processing links file: {str(e)}")
        
        # Try to clean up the temp directory if it's empty
        try:
            if len(os.listdir(self.temp_dir)) == 0:
                os.rmdir(self.temp_dir)
        except:
            pass
            
        return results
    
    def save_results(self, results: List[Dict[str, Any]]) -> Tuple[str, str]:
        """
        Save the results in both pickle and JSON formats
        """
        # Save as pickle
        pickle_path = os.path.join(self.output_dir, "video_data.pkl")
        with open(pickle_path, 'wb') as f:
            pickle.dump(results, f)
        logger.info(f"Saved results as pickle to {pickle_path}")
        
        # Save as JSON (more human-readable and portable)
        json_path = os.path.join(self.output_dir, "video_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved results as JSON to {json_path}")
        
        return pickle_path, json_path
    
    def query_database(self, user: Optional[str] = None, year: Optional[int] = None, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query the database with optional filters
        """
        if not self.db_conn:
            logger.error("Database connection not available")
            return []
            
        cursor = self.db_conn.cursor()
        query = "SELECT * FROM videos WHERE 1=1"
        params = []
        
        if user:
            query += " AND user = ?"
            params.append(user)
        
        if year:
            query += " AND upload_year = ?"
            params.append(year)
        
        if source:
            query += " AND source = ?"
            params.append(source)
        
        cursor.execute(query, params)
        columns = [description[0] for description in cursor.description]
        results = []
        
        for row in cursor.fetchall():
            result = dict(zip(columns, row))
            results.append(result)
        
        return results
    
    def close(self) -> None:
        """
        Close database connection
        """
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None

#%%
def main():
    parser = argparse.ArgumentParser(description='Create GIF previews and download thumbnails from various video sources')
    parser.add_argument('links_file', nargs='?', help='Path to text file containing video links or file paths (one per line)')
    parser.add_argument('--output', '-o', default='./data', help='Output directory for GIF previews and thumbnails')
    parser.add_argument('--user', '-u', default='', help='Username to associate with the videos')
    parser.add_argument('--filter-user', help='Filter results by username (query mode)')
    parser.add_argument('--filter-year', type=int, help='Filter results by upload year (query mode)')
    parser.add_argument('--filter-source', help='Filter results by source (e.g., "youtube", "local")')
    parser.add_argument('--query', action='store_true', help='Run in query mode instead of processing new videos')
    parser.add_argument('--url', help='Process a single URL or file path')
    parser.add_argument('--local-dir', help='Process all video files in a directory')
    
    args = parser.parse_args()
  
    # Validate that at least one input source is provided
    if not args.query and not args.links_file and not args.url and not args.local_dir:
        parser.error("Either 'links_file', '--url', '--local-dir' or '--query' must be provided")
    
    # Create the video preview creator
    preview_creator = VideoPreviewCreator(args.output)
    
    # Query mode
    if args.query:
        logger.info("Running in query mode")
        results = preview_creator.query_database(args.filter_user, args.filter_year, args.filter_source)
        
        print(f"\nFound {len(results)} videos matching your criteria:")
        for i, video in enumerate(results, 1):
            print(f"{i}. User: {video['user']} | Source: {video['source']} | {video['title']} ({video['upload_year']})")
            print(f"   URL: {video['url']}")
            print(f"   Thumbnail: {video['thumb_path']}")
            print(f"   GIF Preview: {video['vid_preview_path']}")
            print()
            
        # Save filtered results to JSON
        filter_desc = []
        if args.filter_user:
            filter_desc.append(f"user_{args.filter_user}")
        if args.filter_year:
            filter_desc.append(f"year_{args.filter_year}")
        if args.filter_source:
            filter_desc.append(f"source_{args.filter_source}")
        
        if filter_desc:
            filename = f"filtered_{'_'.join(filter_desc)}.json"
        else:
            filename = "all_videos.json"
            
        json_path = os.path.join(args.output, filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved filtered results to {json_path}")
    
    # Process a local directory
    elif args.local_dir:
        logger.info(f"Processing all videos in directory: {args.local_dir}")
        
        if not os.path.isdir(args.local_dir):
            logger.error(f"'{args.local_dir}' is not a valid directory")
            return
        
        # Find all video files in the directory
        video_extensions = ['.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv']
        video_files = []
        
        for root, _, files in os.walk(args.local_dir):
            for file in files:
                if any(file.lower().endswith(ext) for ext in video_extensions):
                    video_files.append(os.path.join(root, file))
        
        logger.info(f"Found {len(video_files)} video files in directory")
        
        # Process each video file
        results = []
        for video_file in video_files:
            video_info = preview_creator.process_url(video_file, args.user)
            if video_info:
                results.append(video_info)
        
        if results:
            pickle_path, json_path = preview_creator.save_results(results)
            
            logger.info(f"Processing complete. Processed {len(results)} videos.")
            logger.info(f"Results saved to database and {json_path}")
            
            # Print a summary of the processed videos
            for i, video_info in enumerate(results, 1):
                user_info = f"User: {video_info['user']} | " if video_info['user'] else ""
                year_info = f" ({video_info['upload_year']})" if video_info['upload_year'] else ""
                print(f"{i}. {user_info}Source: {video_info['source']} | {video_info['title']}{year_info}")
                print(f"   Path: {video_info['url']}")
                print(f"   Thumbnail: {video_info['thumb_path']}")
                print(f"   GIF Preview: {video_info['vid_preview_path']}")
                print()
        else:
            logger.info("No videos were processed successfully")
            
    # Process a single URL
    elif args.url:
        logger.info(f"Processing single URL/path: {args.url}")
        video_info = preview_creator.process_url(args.url, args.user)
        results = [video_info] if video_info else []
        
        if results:
            preview_creator.save_results(results)
            
            print(f"\nProcessed 1 video:")
            video = results[0]
            print(f"1. User: {video['user']} | Source: {video['source']} | {video['title']} ({video['upload_year']})")
            print(f"   URL/Path: {video['url']}")
            print(f"   Thumbnail: {video['thumb_path']}")
            print(f"   GIF Preview: {video['vid_preview_path']}")
            print()
        else:
            print("Failed to process URL/path or it was a duplicate")
    
    # Process links file
    else:
        logger.info(f"Starting Video Preview Creator")
        logger.info(f"Links file: {args.links_file}")
        logger.info(f"Output directory: {args.output}")
        if args.user:
            logger.info(f"User: {args.user}")
        
        # Process the links file
        results = preview_creator.process_links_file(args.links_file, args.user)
        
        # Save results to file (in addition to database)
        if results:
            pickle_path, json_path = preview_creator.save_results(results)
            
            logger.info("file saved")
# %%

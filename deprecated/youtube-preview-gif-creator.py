import os
import sys
import random
import json
import sqlite3
from datetime import datetime
from pathlib import Path
import argparse
import pytube
from pytube import YouTube

from moviepy.video.io import VideoFileClip
import logging
import requests
import pickle

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_youtube_video(url, output_dir):
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
        download_thumbnail(thumbnail_url, thumbnail_path)
        
        return output_path, thumbnail_path, video_title, video_description, upload_year
    except Exception as e:
        logger.error(f"Error downloading {url}: {str(e)}")
        return None, None, None, None, None

def download_thumbnail(url, output_path):
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

def create_gif_preview(video_path, output_dir, duration=30):
    """
    Create a 30-second GIF preview from a representative part of the video
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
            clip.close()
        return None

def init_database(db_path):
    """
    Initialize SQLite database with the required schema
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create videos table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS videos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            url TEXT UNIQUE,
            title TEXT,
            description TEXT,
            thumb_path TEXT,
            vid_preview_path TEXT,
            upload_year INTEGER,
            date_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        conn.commit()
        logger.info(f"Database initialized at {db_path}")
        return conn
    except Exception as e:
        logger.error(f"Error initializing database: {str(e)}")
        if 'conn' in locals():
            conn.close()
        return None

def save_to_database(conn, video_info):
    """
    Save a video record to the SQLite database
    """
    try:
        cursor = conn.cursor()
        cursor.execute('''
        INSERT OR REPLACE INTO videos 
        (user, url, title, description, thumb_path, vid_preview_path, upload_year)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            video_info['user'],
            video_info['url'],
            video_info['title'],
            video_info['description'],
            video_info['thumb_path'],
            video_info['vid_preview_path'],
            video_info['upload_year']
        ))
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error saving to database: {str(e)}")
        return None

def process_links_file(links_file, output_dir, db_conn, username=""):
    """
    Process a file containing YouTube links and create GIF previews
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
    
    temp_dir = os.path.join(output_dir, "temp_videos")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    thumbnails_dir = os.path.join(output_dir, "thumbnails")
    if not os.path.exists(thumbnails_dir):
        os.makedirs(thumbnails_dir)
        logger.info(f"Created thumbnails directory: {thumbnails_dir}")
        
    gif_dir = os.path.join(output_dir, "previews")
    if not os.path.exists(gif_dir):
        os.makedirs(gif_dir)
        logger.info(f"Created GIF previews directory: {gif_dir}")
        
    results = []
    
    try:
        with open(links_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                url = line.strip()
                if not url or not url.startswith("http"):
                    logger.warning(f"Line {line_num}: Invalid URL - {url}")
                    continue
                    
                logger.info(f"Processing URL {line_num}: {url}")
                
                # Download the video and thumbnail, get metadata
                video_path, thumbnail_path, video_title, video_description, upload_year = download_youtube_video(url, temp_dir)
                if not video_path:
                    logger.error(f"Failed to download video from {url}")
                    continue
                
                # Create GIF preview
                gif_path = create_gif_preview(video_path, gif_dir)
                
                # Move thumbnail to thumbnails directory
                if thumbnail_path:
                    thumbnail_filename = os.path.basename(thumbnail_path)
                    new_thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
                    os.rename(thumbnail_path, new_thumbnail_path)
                    thumbnail_path = new_thumbnail_path
                
                if gif_path:
                    # Create dictionary with all the information
                    video_info = {
                        "user": username,
                        "url": url,
                        "title": video_title,
                        "description": video_description,
                        "thumb_path": os.path.relpath(thumbnail_path, output_dir),
                        "vid_preview_path": os.path.relpath(gif_path, output_dir),
                        "upload_year": upload_year
                    }
                    results.append(video_info)
                    
                    # Save to database
                    if db_conn:
                        save_to_database(db_conn, video_info)
                
                # Attempt to clean up the video file to save space
                try:
                    os.remove(video_path)
                except Exception as e:
                    logger.warning(f"Could not remove temporary video file {video_path}: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error processing links file: {str(e)}")
    
    # Try to clean up the temp directory if it's empty
    try:
        if len(os.listdir(temp_dir)) == 0:
            os.rmdir(temp_dir)
    except:
        pass
        
    return results

def save_results(results, output_dir):
    """
    Save the results in both pickle and JSON formats
    """
    # Save as pickle
    pickle_path = os.path.join(output_dir, "video_data.pkl")
    with open(pickle_path, 'wb') as f:
        pickle.dump(results, f)
    logger.info(f"Saved results as pickle to {pickle_path}")
    
    # Save as JSON (more human-readable and portable)
    json_path = os.path.join(output_dir, "video_data.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved results as JSON to {json_path}")
    
    return pickle_path, json_path

def query_database(db_conn, user=None, year=None):
    """
    Query the database with optional user and year filters
    """
    cursor = db_conn.cursor()
    query = "SELECT * FROM videos WHERE 1=1"
    params = []
    
    if user:
        query += " AND user = ?"
        params.append(user)
    
    if year:
        query += " AND upload_year = ?"
        params.append(year)
    
    cursor.execute(query, params)
    columns = [description[0] for description in cursor.description]
    results = []
    
    for row in cursor.fetchall():
        result = dict(zip(columns, row))
        results.append(result)
    
    return results

def main():
    parser = argparse.ArgumentParser(description='Create GIF previews and download thumbnails from YouTube videos listed in a text file')
    parser.add_argument('links_file', help='Path to text file containing YouTube links (one per line)')
    parser.add_argument('--output', '-o', default='./data', help='Output directory for GIF previews and thumbnails')
    parser.add_argument('--user', '-u', default='', help='Username to associate with the videos')
    parser.add_argument('--filter-user', help='Filter results by username (query mode)')
    parser.add_argument('--filter-year', type=int, help='Filter results by upload year (query mode)')
    parser.add_argument('--query', action='store_true', help='Run in query mode instead of processing new videos')
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    if not os.path.exists(args.output):
        os.makedirs(args.output)
    
    # Initialize or connect to the database
    db_path = os.path.join(args.output, "videos.db")
    db_conn = init_database(db_path)
    
    if not db_conn:
        logger.error("Failed to initialize database. Exiting.")
        return
    
    # Query mode
    if args.query:
        logger.info("Running in query mode")
        results = query_database(db_conn, args.filter_user, args.filter_year)
        
        print(f"\nFound {len(results)} videos matching your criteria:")
        for i, video in enumerate(results, 1):
            print(f"{i}. User: {video['user']} | {video['title']} ({video['upload_year']})")
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
        
        if filter_desc:
            filename = f"filtered_{'_'.join(filter_desc)}.json"
        else:
            filename = "all_videos.json"
            
        json_path = os.path.join(args.output, filename)
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved filtered results to {json_path}")
        
    # Process mode
    else:
        logger.info(f"Starting YouTube GIF preview creator")
        logger.info(f"Links file: {args.links_file}")
        logger.info(f"Output directory: {args.output}")
        if args.user:
            logger.info(f"User: {args.user}")
        
        # Process the links file
        results = process_links_file(args.links_file, args.output, db_conn, args.user)
        
        # Save results to file (in addition to database)
        pickle_path, json_path = save_results(results, args.output)
        
        logger.info(f"Processing complete. Processed {len(results)} videos.")
        logger.info(f"Results saved to database and {json_path}")
        
        # Print a summary of the processed videos
        for i, video_info in enumerate(results, 1):
            user_info = f"User: {video_info['user']} | " if video_info['user'] else ""
            year_info = f" ({video_info['upload_year']})" if video_info['upload_year'] else ""
            print(f"{i}. {user_info}{video_info['title']}{year_info}")
            print(f"   URL: {video_info['url']}")
            print(f"   Thumbnail: {video_info['thumb_path']}")
            print(f"   GIF Preview: {video_info['vid_preview_path']}")
            print()
    
    # Close the database connection
    db_conn.close()

if __name__ == "__main__":
    main()

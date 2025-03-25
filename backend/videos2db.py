"""
Video Preview ETL Process
========================

This script handles the Extract-Transform-Load (ETL) process for the Video Preview Application:

1. Extract: Downloads videos/metadata from various sources (YouTube, local files)
2. Transform: Generates thumbnails and preview clips
3. Load: Stores the resulting data in an SQLite database and file system

The script can operate in multiple modes:
- Process a list of video URLs/paths from a text file
- Process a single URL or file path
- Process all video files in a directory
- Query the database for existing videos with filtering options
"""
import os
import sys
import json
import logging
import argparse
from typing import List, Dict, Any, Optional

# Adjust the path to ensure we can import from src directory
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)  # Go up one level to project root
src_path = os.path.join(current_dir, "src")
sys.path.append(src_path)
sys.path.append(project_root)
sys.path.append(current_dir)  # Add the backend directory itself

from src.video_processor import VideoProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    """
    Main entry point for the video ETL process.
    
    Parses command line arguments and executes the appropriate processing mode:
    - Query mode: Search existing videos in database
    - Process mode: Process new videos from various sources
    """
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='Process videos and create previews from various sources')
    parser.add_argument('links_file', nargs='?', help='Path to text file containing video links or file paths (one per line)')
    parser.add_argument('--output', '-o', default=os.path.join(os.path.dirname(current_dir), 'data'), 
                        help='Output directory for previews and thumbnails (default: project_root/data)')
    parser.add_argument('--user', '-u', required=True, help='Username to associate with the videos (required)')
    parser.add_argument('--filter-user', help='Filter results by username (query mode)')
    parser.add_argument('--filter-year', type=int, help='Filter results by upload year (query mode)')
    parser.add_argument('--filter-source', help='Filter results by source (e.g., "youtube", "local")')
    parser.add_argument('--query', action='store_true', help='Run in query mode instead of processing new videos')
    parser.add_argument('--url', help='Process a single URL or file path')
    parser.add_argument('--local-dir', help='Process all video files in a directory')
    
    args = parser.parse_args()
    
    # Ensure data directory exists
    output_dir = os.path.abspath(args.output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        logger.info(f"Created output directory: {output_dir}")
  
    # Validate that at least one input source is provided
    if not args.query and not args.links_file and not args.url and not args.local_dir:
        parser.error("Either 'links_file', '--url', '--local-dir' or '--query' must be provided")
    
    # Create the video processor
    processor = VideoProcessor(output_dir)
    logger.info(f"Data will be saved to: {output_dir}")
    
    # Execute in the appropriate mode
    try:
        if args.query:
            _run_query_mode(processor, args, output_dir)
        elif args.local_dir:
            _run_local_dir_mode(processor, args)
        elif args.url:
            _run_single_url_mode(processor, args)
        else:
            _run_links_file_mode(processor, args, output_dir)
    finally:
        # Ensure database connection is closed
        processor.close()

def _run_query_mode(processor, args, output_dir):
    """
    Run in query mode - search existing videos in the database.
    
    Args:
        processor: VideoProcessor instance
        args: Command line arguments
        output_dir: Output directory path
    """
    logger.info("Running in query mode")
    results = processor.query_database(args.filter_user, args.filter_year, args.filter_source)
    
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
        
    # Save to the user directory if a user filter is specified
    if args.filter_user:
        user_dir = os.path.join(output_dir, args.filter_user)
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        json_path = os.path.join(user_dir, filename)
    else:
        json_path = os.path.join(output_dir, filename)
        
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved filtered results to {json_path}")

def _run_local_dir_mode(processor, args):
    """
    Process all video files in a local directory.
    
    Args:
        processor: VideoProcessor instance
        args: Command line arguments
    """
    logger.info(f"Processing all videos in directory: {args.local_dir}")
    
    results = processor.process_local_directory(args.local_dir, args.user)
    
    if results:
        saved_paths = processor.save_results(results, args.user)
        
        logger.info(f"Processing complete. Processed {len(results)} videos.")
        logger.info(f"Results saved to database and {saved_paths['json_path']}")
        
        # Print a summary of the processed videos
        _print_video_summary(results)
    else:
        logger.info("No videos were processed successfully")

def _run_single_url_mode(processor, args):
    """
    Process a single URL or file path.
    
    Args:
        processor: VideoProcessor instance
        args: Command line arguments
    """
    logger.info(f"Processing single URL/path: {args.url}")
    video_info = processor.process_url(args.url, args.user)
    results = [video_info] if video_info else []
    
    if results:
        processor.save_results(results, args.user)
        
        print(f"\nProcessed 1 video:")
        video = results[0]
        print(f"1. User: {video['user']} | Source: {video['source']} | {video['title']} ({video['upload_year']})")
        print(f"   URL/Path: {video['url']}")
        print(f"   Thumbnail: {video['thumb_path']}")
        print(f"   GIF Preview: {video['vid_preview_path']}")
        print()
    else:
        print("Failed to process URL/path or it was a duplicate")

def _run_links_file_mode(processor, args, output_dir):
    """
    Process videos from a text file containing URLs or file paths.
    
    Args:
        processor: VideoProcessor instance
        args: Command line arguments
        output_dir: Output directory path
    """
    logger.info(f"Starting Video Processor")
    logger.info(f"Links file: {args.links_file}")
    logger.info(f"Output directory: {output_dir}")
    logger.info(f"User: {args.user}")
    
    # Process the links file
    results = processor.process_links_file(args.links_file, args.user)
    
    # Save results to file (in addition to database)
    if results:
        saved_paths = processor.save_results(results, args.user)
        logger.info(f"Results saved to {saved_paths['json_path']}")
        _print_video_summary(results)
    else:
        logger.info("No videos were processed successfully")

def _print_video_summary(results):
    """
    Print a summary of processed videos.
    
    Args:
        results: List of video info dictionaries
    """
    print("\nProcessed Video Summary:")
    for i, video_info in enumerate(results, 1):
        year_info = f" ({video_info['upload_year']})" if video_info.get('upload_year') else ""
        print(f"{i}. User: {video_info['user']} | Source: {video_info['source']} | {video_info['title']}{year_info}")
        print(f"   Path: {video_info['url']}")
        print(f"   Thumbnail: {video_info['thumb_path']}")
        print(f"   GIF Preview: {video_info['vid_preview_path']}")
        print()

if __name__ == "__main__":
    main()
"""
This script downloads videos from YouTube and other sources, extracts metadata, and creates GIF previews.
Previews are stored in files and metadata is stored in an SQLite database.
"""
import os
import sys
import json
import logging
import argparse
from typing import List, Dict, Any, Optional

# Ensure src is in the path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.video_processor import VideoProcessor

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description='Create GIF previews and download thumbnails from various video sources')
    parser.add_argument('links_file', nargs='?', help='Path to text file containing video links or file paths (one per line)')
    parser.add_argument('--output', '-o', default='./data', help='Output directory for GIF previews and thumbnails')
    parser.add_argument('--user', '-u', required=True, help='Username to associate with the videos (required)')
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
    
    # Create the video processor
    processor = VideoProcessor(args.output)
    
    # Query mode
    if args.query:
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
            user_dir = os.path.join(args.output, args.filter_user)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)
            json_path = os.path.join(user_dir, filename)
        else:
            json_path = os.path.join(args.output, filename)
            
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved filtered results to {json_path}")
    
    # Process a local directory
    elif args.local_dir:
        logger.info(f"Processing all videos in directory: {args.local_dir}")
        
        results = processor.process_local_directory(args.local_dir, args.user)
        
        if results:
            saved_paths = processor.save_results(results, args.user)
            
            logger.info(f"Processing complete. Processed {len(results)} videos.")
            logger.info(f"Results saved to database and {saved_paths['json_path']}")
            
            # Print a summary of the processed videos
            for i, video_info in enumerate(results, 1):
                year_info = f" ({video_info['upload_year']})" if video_info['upload_year'] else ""
                print(f"{i}. User: {video_info['user']} | Source: {video_info['source']} | {video_info['title']}{year_info}")
                print(f"   Path: {video_info['url']}")
                print(f"   Thumbnail: {video_info['thumb_path']}")
                print(f"   GIF Preview: {video_info['vid_preview_path']}")
                print()
        else:
            logger.info("No videos were processed successfully")
            
    # Process a single URL
    elif args.url:
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
    
    # Process links file
    else:
        logger.info(f"Starting Video Processor")
        logger.info(f"Links file: {args.links_file}")
        logger.info(f"Output directory: {args.output}")
        logger.info(f"User: {args.user}")
        
        # Process the links file
        results = processor.process_links_file(args.links_file, args.user)
        
        # Save results to file (in addition to database)
        if results:
            saved_paths = processor.save_results(results, args.user)
            logger.info(f"Results saved to {saved_paths['json_path']}")
    
    # Close database connection
    processor.close()


if __name__ == "__main__":
    main()
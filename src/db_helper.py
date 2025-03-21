"""
Module for handling database operations for the video preview system.
"""
import os
import sqlite3
import logging
from typing import Optional, Dict, Any, List

# Set up logging
logger = logging.getLogger(__name__)

class DatabaseHelper:
    """
    Class to handle all database operations for the video preview system.
    """
    def __init__(self, db_path: str):
        """
        Initialize the database helper
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self.db_conn = None
        self.init_database()
    
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
                user TEXT NOT NULL,
                url TEXT UNIQUE,
                source TEXT,
                title TEXT,
                description TEXT,
                thumb_path TEXT,
                vid_preview_path TEXT,
                upload_year INTEGER,
                content_hash TEXT,
                preview_type TEXT DEFAULT 'gif',
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
            
            # Create an index on user for faster filtering
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_user ON videos (user)")
            
            self.db_conn.commit()
            logger.info(f"Database initialized at {self.db_path}")
        except Exception as e:
            logger.error(f"Error initializing database: {str(e)}")
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None
    
    def is_duplicate(self, url: str, content_hash: str) -> bool:
        """
        Check if a video is already in the database by URL or content hash
        
        Args:
            url: URL or path of the video
            content_hash: Hash of the video content
            
        Returns:
            True if video is a duplicate, False otherwise
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
        
        Args:
            video_info: Dictionary containing video metadata
            
        Returns:
            ID of the new record, or None if save failed
        """
        if not self.db_conn:
            logger.error("Database connection not available")
            return None
            
        try:
            cursor = self.db_conn.cursor()
            # Check if preview_type column exists
            try:
                cursor.execute("SELECT preview_type FROM videos LIMIT 1")
            except sqlite3.OperationalError:
                cursor.execute("ALTER TABLE videos ADD COLUMN preview_type TEXT DEFAULT 'gif'")
                logger.info("Added preview_type column to database schema")
            
            cursor.execute('''
            INSERT OR REPLACE INTO videos 
            (user, url, source, title, description, thumb_path, vid_preview_path, upload_year, content_hash, preview_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                video_info['user'],
                video_info['url'],
                video_info['source'],
                video_info['title'],
                video_info['description'],
                video_info['thumb_path'],
                video_info['vid_preview_path'],
                video_info['upload_year'],
                video_info.get('content_hash', ''),
                video_info.get('preview_type', 'gif')
            ))
            self.db_conn.commit()
            return cursor.lastrowid
        except Exception as e:
            logger.error(f"Error saving to database: {str(e)}")
            return None
    
    def query_database(self, user: Optional[str] = None, year: Optional[int] = None, source: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Query the database with optional filters
        
        Args:
            user: Filter by username
            year: Filter by upload year
            source: Filter by source type
            
        Returns:
            List of dictionaries containing video records
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
    
    def delete_video(self, video_id: int) -> bool:
        """
        Delete a video entry from the database
        
        Args:
            video_id: ID of the video to delete
            
        Returns:
            True if deletion was successful, False otherwise
        """
        if not self.db_conn:
            logger.error("Database connection not available")
            return False
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("DELETE FROM videos WHERE id = ?", (video_id,))
            self.db_conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"Error deleting video with ID {video_id}: {str(e)}")
            return False
    
    def get_video_by_id(self, video_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a video by its ID
        
        Args:
            video_id: ID of the video to retrieve
            
        Returns:
            Dictionary with video data or None if not found
        """
        if not self.db_conn:
            logger.error("Database connection not available")
            return None
        
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("SELECT * FROM videos WHERE id = ?", (video_id,))
            row = cursor.fetchone()
            
            if not row:
                return None
                
            columns = [description[0] for description in cursor.description]
            return dict(zip(columns, row))
        except Exception as e:
            logger.error(f"Error retrieving video with ID {video_id}: {str(e)}")
            return None
    
    def get_videos_by_user(self, username: str) -> List[Dict[str, Any]]:
        """
        Get all videos for a specific user
        
        Args:
            username: Username to filter by
            
        Returns:
            List of dictionaries containing video records
        """
        return self.query_database(user=username)
    
    def close(self) -> None:
        """
        Close database connection
        """
        if self.db_conn:
            self.db_conn.close()
            self.db_conn = None
            logger.info("Database connection closed")
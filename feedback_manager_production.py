#!/usr/bin/env python3
"""
Production-ready Feedback Manager for Railway deployment
Uses environment variable for database path to support Railway volumes
"""

import os
from pathlib import Path
from feedback_manager import FeedbackManager

class ProductionFeedbackManager(FeedbackManager):
    def __init__(self):
        """
        Initialize feedback manager with production settings
        Uses FEEDBACK_DB_PATH env var or falls back to /data/feedback.db for Railway volume
        """
        # Railway volume mount point or local fallback
        db_path = os.getenv('FEEDBACK_DB_PATH', '/data/feedback.db')
        
        # Ensure directory exists
        db_dir = Path(db_path).parent
        db_dir.mkdir(parents=True, exist_ok=True)
        
        # Backup directory in the same volume
        backup_dir = db_dir / 'feedback_backups'
        
        print(f"📊 Initializing feedback database at: {db_path}")
        print(f"💾 Backup directory: {backup_dir}")
        
        super().__init__(db_path=str(db_path), backup_dir=str(backup_dir))

def get_feedback_manager():
    """Factory function to get appropriate feedback manager based on environment"""
    if os.getenv('RAILWAY_ENVIRONMENT') or os.getenv('PRODUCTION'):
        return ProductionFeedbackManager()
    else:
        # Local development
        return FeedbackManager()

if __name__ == "__main__":
    # Test the production manager
    manager = get_feedback_manager()
    print(f"✅ Feedback manager initialized")
    print(f"📁 Database size: {manager.get_database_size()} bytes")
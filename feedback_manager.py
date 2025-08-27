#!/usr/bin/env python3
"""
Feedback Manager for Mozilla Support Bot
Handles feedback collection, session tracking, and data storage
"""

import sqlite3
import json
import uuid
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class FeedbackManager:
    def __init__(self, db_path: str = "feedback.db", backup_dir: str = "feedback_backups"):
        """
        Initialize the feedback manager with SQLite database
        
        Args:
            db_path: Path to SQLite database file
            backup_dir: Directory for JSON backups
        """
        self.db_path = db_path
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(exist_ok=True)
        
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sessions table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_agent TEXT,
                    ip_hash TEXT,
                    metadata TEXT
                )
            """)
            
            # Conversations table (with trace_data column)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    message_number INTEGER,
                    query TEXT,
                    response TEXT,
                    model TEXT,
                    response_time_ms INTEGER,
                    sources TEXT,
                    trace_data TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    error BOOLEAN DEFAULT 0,
                    FOREIGN KEY (session_id) REFERENCES sessions(id)
                )
            """)
            
            # Feedback table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS feedback (
                    id TEXT PRIMARY KEY,
                    conversation_id TEXT,
                    feedback_type TEXT,
                    rating INTEGER,
                    comment TEXT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sessions_started 
                ON sessions(started_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_conversations_session 
                ON conversations(session_id, message_number)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_feedback_conversation 
                ON feedback(conversation_id)
            """)
            
            # Add trace_data column if it doesn't exist (for migration)
            cursor.execute("""
                PRAGMA table_info(conversations)
            """)
            columns = [col[1] for col in cursor.fetchall()]
            if 'trace_data' not in columns:
                cursor.execute("""
                    ALTER TABLE conversations ADD COLUMN trace_data TEXT
                """)
                logger.info("Added trace_data column to conversations table")
            
            conn.commit()
    
    def create_session(self, user_agent: str = None, ip_address: str = None) -> str:
        """
        Create a new session
        
        Args:
            user_agent: User-Agent string from request
            ip_address: IP address (will be hashed)
            
        Returns:
            Session ID
        """
        session_id = str(uuid.uuid4())
        ip_hash = None
        
        if ip_address:
            # Hash IP for privacy
            ip_hash = hashlib.sha256(ip_address.encode()).hexdigest()[:16]
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sessions (id, user_agent, ip_hash, started_at)
                VALUES (?, ?, ?, ?)
            """, (session_id, user_agent, ip_hash, datetime.now()))
            conn.commit()
        
        logger.info(f"Created new session: {session_id}")
        return session_id
    
    def save_conversation(self, 
                         session_id: str,
                         query: str,
                         response: str,
                         model: str,
                         response_time_ms: int,
                         sources: List[Dict[str, str]] = None,
                         trace_data: Dict[str, Any] = None,
                         error: bool = False,
                         message_number: int = None) -> str:
        """
        Save a conversation turn
        
        Args:
            session_id: Session ID
            query: User query
            response: Bot response
            model: Model used (e.g., "gpt-5")
            response_time_ms: Response time in milliseconds
            sources: List of source documents used
            trace_data: Agent trace data with spans and tool calls
            error: Whether an error occurred
            message_number: Message number in conversation (auto-increments if None)
            
        Returns:
            Conversation ID
        """
        conversation_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get message number if not provided
            if message_number is None:
                cursor.execute("""
                    SELECT COALESCE(MAX(message_number), 0) + 1
                    FROM conversations
                    WHERE session_id = ?
                """, (session_id,))
                message_number = cursor.fetchone()[0]
            
            # Store sources and trace_data as JSON
            sources_json = json.dumps(sources) if sources else None
            trace_data_json = json.dumps(trace_data) if trace_data else None
            
            cursor.execute("""
                INSERT INTO conversations 
                (id, session_id, message_number, query, response, model, 
                 response_time_ms, sources, trace_data, error, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (conversation_id, session_id, message_number, query, response, 
                  model, response_time_ms, sources_json, trace_data_json, error, datetime.now()))
            conn.commit()
        
        logger.info(f"Saved conversation {conversation_id} for session {session_id}")
        return conversation_id
    
    def add_feedback(self,
                    conversation_id: str,
                    feedback_type: str,
                    rating: int = None,
                    comment: str = None) -> str:
        """
        Add feedback for a conversation
        
        Args:
            conversation_id: Conversation ID
            feedback_type: 'positive', 'negative', or 'neutral'
            rating: Optional rating (1-5)
            comment: Optional text comment
            
        Returns:
            Feedback ID
        """
        feedback_id = str(uuid.uuid4())
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO feedback (id, conversation_id, feedback_type, rating, comment, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (feedback_id, conversation_id, feedback_type, rating, comment, datetime.now()))
            conn.commit()
        
        logger.info(f"Added {feedback_type} feedback for conversation {conversation_id}")
        return feedback_id
    
    def get_session_conversations(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all conversations for a session"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT c.*, f.feedback_type, f.rating, f.comment
                FROM conversations c
                LEFT JOIN feedback f ON c.id = f.conversation_id
                WHERE c.session_id = ?
                ORDER BY c.message_number
            """, (session_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_feedback_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get feedback statistics
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with statistics
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Total conversations
            cursor.execute("""
                SELECT COUNT(*) FROM conversations
                WHERE timestamp > datetime('now', '-' || ? || ' days')
            """, (days,))
            total_conversations = cursor.fetchone()[0]
            
            # Feedback breakdown
            cursor.execute("""
                SELECT feedback_type, COUNT(*) as count
                FROM feedback
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                GROUP BY feedback_type
            """, (days,))
            feedback_breakdown = dict(cursor.fetchall())
            
            # Average response time
            cursor.execute("""
                SELECT AVG(response_time_ms) as avg_time
                FROM conversations
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                AND error = 0
            """, (days,))
            avg_response_time = cursor.fetchone()[0]
            
            # Most used model
            cursor.execute("""
                SELECT model, COUNT(*) as count
                FROM conversations
                WHERE timestamp > datetime('now', '-' || ? || ' days')
                GROUP BY model
                ORDER BY count DESC
                LIMIT 1
            """, (days,))
            result = cursor.fetchone()
            most_used_model = result[0] if result else None
            
            # Error rate
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN error = 1 THEN 1 ELSE 0 END) as errors,
                    COUNT(*) as total
                FROM conversations
                WHERE timestamp > datetime('now', '-' || ? || ' days')
            """, (days,))
            errors, total = cursor.fetchone()
            error_rate = (errors / total * 100) if total > 0 else 0
            
            return {
                'total_conversations': total_conversations,
                'feedback_breakdown': feedback_breakdown,
                'avg_response_time_ms': avg_response_time,
                'most_used_model': most_used_model,
                'error_rate': error_rate,
                'satisfaction_rate': self._calculate_satisfaction_rate(feedback_breakdown)
            }
    
    def _calculate_satisfaction_rate(self, feedback_breakdown: Dict[str, int]) -> float:
        """Calculate satisfaction rate from feedback breakdown"""
        positive = feedback_breakdown.get('positive', 0)
        negative = feedback_breakdown.get('negative', 0)
        total = positive + negative
        
        if total == 0:
            return 0.0
        
        return (positive / total) * 100
    
    def backup_to_json(self, days_to_keep: int = 7):
        """
        Backup old data to JSON and clean up database
        
        Args:
            days_to_keep: Number of days of data to keep in SQLite
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"feedback_backup_{timestamp}.json"
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get old data
            cursor.execute("""
                SELECT * FROM conversations
                WHERE timestamp < datetime('now', '-' || ? || ' days')
            """, (days_to_keep,))
            old_conversations = [dict(row) for row in cursor.fetchall()]
            
            if old_conversations:
                # Get related feedback
                conv_ids = [c['id'] for c in old_conversations]
                placeholders = ','.join('?' * len(conv_ids))
                cursor.execute(f"""
                    SELECT * FROM feedback
                    WHERE conversation_id IN ({placeholders})
                """, conv_ids)
                old_feedback = [dict(row) for row in cursor.fetchall()]
                
                # Save to JSON
                backup_data = {
                    'backup_date': timestamp,
                    'conversations': old_conversations,
                    'feedback': old_feedback
                }
                
                with open(backup_file, 'w') as f:
                    json.dump(backup_data, f, indent=2, default=str)
                
                # Delete old data
                cursor.execute(f"""
                    DELETE FROM feedback
                    WHERE conversation_id IN ({placeholders})
                """, conv_ids)
                cursor.execute("""
                    DELETE FROM conversations
                    WHERE timestamp < datetime('now', '-' || ? || ' days')
                """, (days_to_keep,))
                
                conn.commit()
                logger.info(f"Backed up {len(old_conversations)} conversations to {backup_file}")
    
    def get_database_size(self) -> int:
        """Get database file size in bytes"""
        return Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
    
    def should_rotate(self, max_size_mb: int = 100) -> bool:
        """Check if database should be rotated based on size"""
        size_mb = self.get_database_size() / (1024 * 1024)
        return size_mb > max_size_mb
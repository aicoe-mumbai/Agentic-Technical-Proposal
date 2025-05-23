import sqlite3
from contextlib import contextmanager
from Backend.app.core.config import DB_FILE
import datetime
from Backend.app.db.migrations import apply_migrations
from typing import Optional, Dict, List, Any

def init_db():
    """Initialize database and create tables if they don't exist"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Existing templates table
        cursor.execute('''CREATE TABLE IF NOT EXISTS templates 
                         (project_name TEXT PRIMARY KEY, 
                          project_TOC TEXT, 
                          file_path TEXT)''')
                          
        # New table for documents
        cursor.execute('''CREATE TABLE IF NOT EXISTS documents
                         (doc_id TEXT PRIMARY KEY,
                          filename TEXT,
                          file_path TEXT,
                          status TEXT,
                          message TEXT,
                          total_pages INTEGER,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                          
        # New table for document scope
        cursor.execute('''CREATE TABLE IF NOT EXISTS document_scope
                         (doc_id TEXT PRIMARY KEY,
                          scope_text TEXT,
                          source_pages TEXT,
                          is_confirmed BOOLEAN DEFAULT FALSE,
                          FOREIGN KEY(doc_id) REFERENCES documents(doc_id))''')
                          
        # New table for document topics
        cursor.execute('''CREATE TABLE IF NOT EXISTS document_topics
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          doc_id TEXT,
                          template_name TEXT,
                          topic_number TEXT,
                          topic_text TEXT,
                          topic_level INTEGER,
                          status TEXT,
                          page INTEGER,
                          is_confirmed BOOLEAN DEFAULT TRUE,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          FOREIGN KEY(doc_id) REFERENCES documents(doc_id))''')
                          
        # New table for generated content
        cursor.execute('''CREATE TABLE IF NOT EXISTS document_content
                         (id INTEGER PRIMARY KEY AUTOINCREMENT,
                          doc_id TEXT,
                          topic_id INTEGER,
                          content TEXT,
                          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                          FOREIGN KEY(doc_id) REFERENCES documents(doc_id),
                          FOREIGN KEY(topic_id) REFERENCES document_topics(id))''')
        
        conn.commit()

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()

def save_template(project_name, project_format, file_path):
    """Save or update a project template in the database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO templates (project_name, project_TOC, file_path) VALUES (?, ?, ?)
                       ON CONFLICT(project_name) DO UPDATE SET project_TOC = ?, file_path = ?''',
                       (project_name, project_format, file_path, project_format, file_path))
        conn.commit()

def get_all_templates():
    """Get all templates from the database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT project_name, project_TOC, file_path FROM templates''')
        data = cursor.fetchall()
        return {name: {"project_TOC": toc, "file_path": file_path} for name, toc, file_path in data}

def get_template_by_name(project_name):
    """Get a specific template by name"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT project_name, project_TOC, file_path FROM templates WHERE project_name = ?''', 
                       (project_name,))
        data = cursor.fetchone()
        if data:
            name, toc, file_path = data
            return {"project_name": name, "project_TOC": toc, "file_path": file_path}
        return None

def delete_template(project_name):
    """Delete a template from the database"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''DELETE FROM templates WHERE project_name = ?''', (project_name,))
        conn.commit()
        return cursor.rowcount > 0

def get_all_documents_summary() -> List[Dict[str, Any]]:
    """Get a summary list of all documents from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Fetching fields relevant for a dashboard summary, ordered by creation time descending
        cursor.execute('''SELECT doc_id, filename, status, created_at, total_pages 
                         FROM documents 
                         ORDER BY created_at DESC''')
        columns = [column[0] for column in cursor.description]
        documents = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return documents

# Document operations
def save_document(doc_id: str, filename: str, file_path: str, status: str = "uploading", message: str = None) -> None:
    """Save or update document information"""
    current_time = datetime.datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO documents (doc_id, filename, file_path, status, message, last_accessed)
                         VALUES (?, ?, ?, ?, ?, ?)
                         ON CONFLICT(doc_id) DO UPDATE SET 
                         status = ?, message = ?, last_accessed = ?''',
                         (doc_id, filename, file_path, status, message, current_time, 
                          status, message, current_time))
        conn.commit()

def get_document(doc_id: str) -> dict:
    """Get document information and update last_accessed timestamp"""
    current_time = datetime.datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT doc_id, filename, file_path, status, message, total_pages 
                         FROM documents WHERE doc_id = ?''', (doc_id,))
        data = cursor.fetchone()
        
        if data:
            # Update last_accessed timestamp
            cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                          (current_time, doc_id))
            conn.commit()
            
            return {
                "doc_id": data[0],
                "filename": data[1],
                "file_path": data[2],
                "status": data[3],
                "message": data[4],
                "total_pages": data[5]
            }
        return None

def update_document_status(doc_id: str, status: str, message: str = None, total_pages: int = None) -> None:
    """Update document processing status"""
    current_time = datetime.datetime.now().isoformat()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if total_pages is not None:
            cursor.execute('''UPDATE documents SET status = ?, message = ?, total_pages = ?, last_accessed = ?
                            WHERE doc_id = ?''', (status, message, total_pages, current_time, doc_id))
        else:
            cursor.execute('''UPDATE documents SET status = ?, message = ?, last_accessed = ?
                            WHERE doc_id = ?''', (status, message, current_time, doc_id))
        conn.commit()

# Scope operations
def save_document_scope(doc_id: str, scope_text: str, source_pages: list, is_confirmed: bool = False) -> None:
    """Save or update document scope"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''INSERT INTO document_scope (doc_id, scope_text, source_pages, is_confirmed)
                         VALUES (?, ?, ?, ?)
                         ON CONFLICT(doc_id) DO UPDATE SET 
                         scope_text = ?, source_pages = ?, is_confirmed = ?''',
                         (doc_id, scope_text, ','.join(map(str, source_pages)), is_confirmed,
                          scope_text, ','.join(map(str, source_pages)), is_confirmed))
        conn.commit()
        
        # Update document last_accessed timestamp
        current_time = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                      (current_time, doc_id))
        conn.commit()

def get_document_scope(doc_id: str) -> dict:
    """Get document scope information"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT scope_text, source_pages, is_confirmed FROM document_scope WHERE doc_id = ?', (doc_id,))
        data = cursor.fetchone()
        
        if data:
            # Update document last_accessed timestamp
            current_time = datetime.datetime.now().isoformat()
            cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                          (current_time, doc_id))
            conn.commit()
            
            return {
                "scope_text": data[0],
                "source_pages": [int(p) for p in data[1].split(',') if p],
                "is_confirmed": bool(data[2]),
                "is_complete": True  # Always set is_complete to True for existing data
            }
        return None

# Topic operations
def save_document_topics(doc_id: str, template_name: str, topics: list) -> None:
    """Save document topics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # First delete existing topics for this document and template
        cursor.execute('DELETE FROM document_topics WHERE doc_id = ? AND template_name = ?', 
                      (doc_id, template_name))
        
        # Insert new topics
        for topic in topics:
            cursor.execute('''INSERT INTO document_topics 
                            (doc_id, template_name, topic_number, topic_text, topic_level, status, page, is_confirmed)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                            (doc_id, template_name, topic.get('number'), topic.get('text'),
                             topic.get('level'), topic.get('status'), topic.get('page'), 
                             topic.get('is_confirmed', True)))
        
        # Update document last_accessed timestamp
        current_time = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                      (current_time, doc_id))
        conn.commit()

def get_document_topics(doc_id: str, template_name: str) -> list:
    """Get document topics"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT topic_number, topic_text, topic_level, status, page, id, is_confirmed
                         FROM document_topics 
                         WHERE doc_id = ? AND template_name = ?
                         ORDER BY id''', (doc_id, template_name))
        
        topics = [{
            "number": row[0],
            "text": row[1],
            "level": row[2],
            "status": row[3],
            "page": row[4],
            "id": row[5],
            "is_confirmed": bool(row[6])
        } for row in cursor.fetchall()]
        
        if topics:
            # Update document last_accessed timestamp
            current_time = datetime.datetime.now().isoformat()
            cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                          (current_time, doc_id))
            conn.commit()
        
        return topics

# Content operations
def save_document_content(doc_id: str, topic_id: int, content: str) -> None:
    """Save or update document content for a topic"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Use INSERT OR REPLACE which works with either primary key or unique constraint
        cursor.execute('''INSERT OR REPLACE INTO document_content (doc_id, topic_id, content)
                         VALUES (?, ?, ?)''',
                         (doc_id, topic_id, content))
        
        # Update document last_accessed timestamp
        current_time = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                      (current_time, doc_id))
        conn.commit()

def get_document_content(doc_id: str, topic_id: int) -> Optional[str]:
    """Get document content for a topic"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''SELECT content FROM document_content 
                         WHERE doc_id = ? AND topic_id = ?''',
                         (doc_id, topic_id))
        result = cursor.fetchone()
        
        # Update document last_accessed timestamp
        current_time = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                      (current_time, doc_id))
        conn.commit()
        
        return result[0] if result else None

def get_all_document_content(doc_id: str) -> Dict[int, str]:
    """Get all content for a document"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT topic_id, content FROM document_content WHERE doc_id = ?', (doc_id,))
        results = cursor.fetchall()
        
        # Update document last_accessed timestamp
        current_time = datetime.datetime.now().isoformat()
        cursor.execute('UPDATE documents SET last_accessed = ? WHERE doc_id = ?', 
                      (current_time, doc_id))
        conn.commit()
        
        return {row[0]: row[1] for row in results}

# Apply database migrations instead of directly initializing the DB
apply_migrations()
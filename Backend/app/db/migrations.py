import sqlite3
import os
import time
from contextlib import contextmanager
from Backend.app.core.config import DB_FILE

@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = sqlite3.connect(DB_FILE)
    try:
        yield conn
    finally:
        conn.close()

def init_migrations_table():
    """Create a migrations table to track applied migrations"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS migrations
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        migration_name TEXT UNIQUE,
                        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        conn.commit()

def is_migration_applied(migration_name):
    """Check if a migration has already been applied"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM migrations WHERE migration_name = ?', (migration_name,))
        return cursor.fetchone() is not None

def record_migration(migration_name):
    """Record that a migration has been applied"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('INSERT INTO migrations (migration_name) VALUES (?)', (migration_name,))
        conn.commit()

def migration_001_initial_schema():
    """Initial schema migration"""
    if is_migration_applied('001_initial_schema'):
        return
    
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
                        
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
    
    record_migration('001_initial_schema')
    print("Applied migration: 001_initial_schema")

def migration_002_add_is_confirmed_to_topics():
    """Add is_confirmed column to document_topics table"""
    if is_migration_applied('002_add_is_confirmed_to_topics'):
        return
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if column exists first
        cursor.execute('PRAGMA table_info(document_topics)')
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'is_confirmed' not in columns:
            cursor.execute('ALTER TABLE document_topics ADD COLUMN is_confirmed BOOLEAN DEFAULT FALSE')
            conn.commit()
    
    record_migration('002_add_is_confirmed_to_topics')
    print("Applied migration: 002_add_is_confirmed_to_topics")

def migration_003_add_last_accessed_to_documents():
    """Add last_accessed column to documents table"""
    if is_migration_applied('003_add_last_accessed_to_documents'):
        return
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Check if column exists first
        cursor.execute('PRAGMA table_info(documents)')
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'last_accessed' not in columns:
            cursor.execute('ALTER TABLE documents ADD COLUMN last_accessed TIMESTAMP')
            conn.commit()
    
    record_migration('003_add_last_accessed_to_documents')
    print("Applied migration: 003_add_last_accessed_to_documents")

def migration_004_add_unique_constraint_to_document_content():
    """Add unique constraint to document_content for doc_id and topic_id"""
    if is_migration_applied('004_add_unique_constraint_to_document_content'):
        return
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create a new table with the unique constraint
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS document_content_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                doc_id TEXT,
                topic_id INTEGER,
                content TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(doc_id) REFERENCES documents(doc_id),
                FOREIGN KEY(topic_id) REFERENCES document_topics(id),
                UNIQUE(doc_id, topic_id)
            )
        ''')
        
        # Copy data from old table to new table
        cursor.execute('''
            INSERT OR IGNORE INTO document_content_new (id, doc_id, topic_id, content, created_at)
            SELECT id, doc_id, topic_id, content, created_at FROM document_content
        ''')
        
        # Drop old table and rename new table
        cursor.execute('DROP TABLE IF EXISTS document_content')
        cursor.execute('ALTER TABLE document_content_new RENAME TO document_content')
        
        conn.commit()
    
    record_migration('004_add_unique_constraint_to_document_content')
    print("Applied migration: 004_add_unique_constraint_to_document_content")

def apply_migrations():
    """Apply all migrations in sequence"""
    print("Checking and applying database migrations...")
    init_migrations_table()
    
    # List migrations in order
    migrations = [
        migration_001_initial_schema,
        migration_002_add_is_confirmed_to_topics,
        migration_003_add_last_accessed_to_documents,
        migration_004_add_unique_constraint_to_document_content
    ]
    
    # Apply each migration
    for migration in migrations:
        migration()
    
    print("Database migrations complete.")

# Run migrations when module is imported
if __name__ != "__main__":  # Don't run when file is executed directly
    apply_migrations() 
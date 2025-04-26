import sqlite3
from contextlib import contextmanager
from Backend.app.core.config import DB_FILE

def init_db():
    """Initialize database and create tables if they don't exist"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS templates 
                         (project_name TEXT PRIMARY KEY, 
                          project_TOC TEXT, 
                          file_path TEXT)''')
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

# Initialize the database on module import
init_db() 
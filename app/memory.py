"""
app/memory.py
-------------
Level 3 Personal Memory & Persistence Engine for Maverick.
Manages long-term storage of user facts, preferences, background details,
and user-defined memories using a local SQLite database.
"""

import sqlite3
from typing import List, Dict, Any, Optional
from app.config import Config


class MemoryEngine:
    """
    MemoryEngine provides persistent long-term memory for Maverick.
    Stores and retrieves user facts, preferences, and personal details across restarts.
    """

    def __init__(self, db_path: Optional[str] = None):
        """Initialize connection to SQLite database and ensure table schema exists."""
        self.db_path = str(db_path) if db_path else str(Config.get_memory_db_path())
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a database connection with dictionary row formatting."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Creates the `memories` table schema if it does not already exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    category TEXT NOT NULL DEFAULT 'fact',
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key) ON CONFLICT REPLACE
                );
            """)
            conn.commit()

    def add_memory(self, key: str, value: str, category: str = "fact") -> int:
        """
        Stores or updates a long-term memory item in the database.

        Parameters:
            key (str): Short descriptor or title (e.g. 'User Name', 'Favorite Language').
            value (str): Memory content (e.g. 'Jivesh', 'Python').
            category (str): Category grouping (e.g. 'personal', 'preference', 'project', 'fact').

        Returns:
            int: The unique row ID of the saved memory.
        """
        clean_key = key.strip()
        clean_val = value.strip()
        clean_cat = category.strip().lower()

        if not clean_key or not clean_val:
            raise ValueError("Memory key and value cannot be empty.")

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO memories (category, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(category, key) DO UPDATE SET
                    value = excluded.value,
                    created_at = CURRENT_TIMESTAMP;
                """,
                (clean_cat, clean_key, clean_val)
            )
            conn.commit()
            return cursor.lastrowid

    def get_all_memories(self) -> List[Dict[str, Any]]:
        """Retrieves all stored long-term memories sorted by category and key."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, category, key, value, created_at FROM memories ORDER BY category, key;"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def search_memories(self, query: str) -> List[Dict[str, Any]]:
        """
        Searches memory key, value, or category for string matches.

        Parameters:
            query (str): Keyword or phrase to search.

        Returns:
            List[Dict[str, Any]]: Matching memory records.
        """
        clean_q = f"%{query.strip().lower()}%"
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, category, key, value, created_at
                FROM memories
                WHERE LOWER(key) LIKE ? OR LOWER(value) LIKE ? OR LOWER(category) LIKE ?
                ORDER BY created_at DESC;
                """,
                (clean_q, clean_q, clean_q)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def delete_memory(self, identifier: str) -> bool:
        """
        Deletes a memory by numeric ID or matching key.

        Parameters:
            identifier (str): Numeric ID string or memory key name.

        Returns:
            bool: True if a memory row was deleted, False otherwise.
        """
        clean_id = identifier.strip()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            if clean_id.isdigit():
                cursor.execute("DELETE FROM memories WHERE id = ?;", (int(clean_id),))
            else:
                cursor.execute("DELETE FROM memories WHERE LOWER(key) = LOWER(?);", (clean_id,))
            conn.commit()
            return cursor.rowcount > 0

    def clear_all(self) -> int:
        """Deletes all memories from the database. Returns count of removed items."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM memories;")
            count = cursor.rowcount
            conn.commit()
            return count

    def get_count(self) -> int:
        """Returns total count of stored long-term memories."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM memories;")
            return cursor.fetchone()[0]

    def format_memories_for_prompt(self, query: Optional[str] = None) -> str:
        """
        Formats memories into a clean Markdown block to inject into the LLM system prompt context.

        Parameters:
            query (Optional[str]): Optional user query to filter relevant memories.

        Returns:
            str: Formatted context string, or empty string if no memories exist.
        """
        if query:
            memories = self.search_memories(query)
            # Fall back to all memories if specific search yields nothing
            if not memories:
                memories = self.get_all_memories()
        else:
            memories = self.get_all_memories()

        if not memories:
            return ""

        formatted_lines = [
            "\n[LONG-TERM PERSONAL MEMORY]",
            "The following facts are remembered about the user across conversations. Use them to personalize your answers without explicitly reciting the memory list:"
        ]
        for m in memories:
            formatted_lines.append(f"- {m['key']}: {m['value']} ({m['category']})")

        return "\n".join(formatted_lines)

import sqlite3
from pathlib import Path
from datetime import datetime
from core.logger import get_logger

logger = get_logger("data.posts_db")

DB_FILE = Path("data/posts.db")


class PostsDB:
    """
    Base de données SQLite pour stocker les posts et leurs stats.
    """

    def __init__(self):
        DB_FILE.parent.mkdir(exist_ok=True)
        self.conn = sqlite3.connect(DB_FILE)
        self._create_tables()
        logger.info("PostsDB initialisée")

    def _create_tables(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                type TEXT NOT NULL,
                sujet TEXT NOT NULL,
                contenu TEXT NOT NULL,
                url TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_id INTEGER NOT NULL,
                scraped_at TEXT NOT NULL,
                likes INTEGER DEFAULT 0,
                commentaires INTEGER DEFAULT 0,
                republications INTEGER DEFAULT 0,
                vues INTEGER DEFAULT 0,
                FOREIGN KEY (post_id) REFERENCES posts(id)
            )
        """)
        self.conn.commit()

    def save_post(self, post_type: str, sujet: str, contenu: str, url: str = None) -> int:
        """Sauvegarde un post publié et retourne son id."""
        cursor = self.conn.execute("""
            INSERT INTO posts (date, type, sujet, contenu, url)
            VALUES (?, ?, ?, ?, ?)
        """, (datetime.now().strftime("%Y-%m-%d"), post_type, sujet, contenu, url))
        self.conn.commit()
        post_id = cursor.lastrowid
        logger.info(f"Post sauvegardé en base (id={post_id})")
        return post_id

    def save_stats(self, post_id: int, likes: int, commentaires: int,
                   republications: int, vues: int):
        """Sauvegarde les stats d'un post."""
        self.conn.execute("""
            INSERT INTO stats (post_id, scraped_at, likes, commentaires, republications, vues)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (post_id, datetime.now().isoformat(), likes, commentaires, republications, vues))
        self.conn.commit()
        logger.info(f"Stats sauvegardées pour post_id={post_id}")

    def get_all_posts(self) -> list:
        """Retourne tous les posts avec leurs dernières stats."""
        cursor = self.conn.execute("""
            SELECT 
                p.id,
                p.date,
                p.type,
                p.sujet,
                p.contenu,
                p.url,
                COALESCE(s.likes, 0) as likes,
                COALESCE(s.commentaires, 0) as commentaires,
                COALESCE(s.republications, 0) as republications,
                COALESCE(s.vues, 0) as vues,
                s.scraped_at
            FROM posts p
            LEFT JOIN (
                SELECT post_id, likes, commentaires, republications, vues, scraped_at,
                       ROW_NUMBER() OVER (PARTITION BY post_id ORDER BY scraped_at DESC) as rn
                FROM stats
            ) s ON p.id = s.post_id AND s.rn = 1
            ORDER BY p.date DESC
        """)
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_post_history(self, post_id: int) -> list:
        """Retourne l'historique des stats d'un post (pour voir l'évolution)."""
        cursor = self.conn.execute("""
            SELECT scraped_at, likes, commentaires, republications, vues
            FROM stats
            WHERE post_id = ?
            ORDER BY scraped_at ASC
        """, (post_id,))
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def close(self):
        self.conn.close()
"""
database.py - ניהול דאטאבייס SQLite לשמירת פוסטים
"""

import sqlite3
from datetime import datetime
import os


class PostDatabase:
    """מחלקה לניהול דאטאבייס הפוסטים"""

    def __init__(self, db_path="posts.db"):
        """
        אתחול הדאטאבייס

        Args:
            db_path: נתיב לקובץ הדאטאבייס
        """
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        """יוצר את הטבלאות אם לא קיימות"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # טבלת פוסטים
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_url TEXT UNIQUE,
                post_id TEXT,
                content TEXT,
                author TEXT,
                group_name TEXT,
                blacklist_match TEXT,
                is_relevant INTEGER DEFAULT 1,
                scanned_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # טבלת הגדרות (לשמירת "פוסט אחרון")
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        conn.commit()
        conn.close()

    def save_post(self, post_data):
        """
        שומר פוסט בדאטאבייס

        Args:
            post_data: dictionary עם נתוני הפוסט

        Returns:
            True אם נשמר בהצלחה, False אם כבר קיים
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute('''
                INSERT INTO posts (post_url, post_id, content, author, group_name, 
                                   blacklist_match, is_relevant, scanned_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data.get('post_url'),
                post_data.get('post_id'),
                post_data.get('content'),
                post_data.get('author'),
                post_data.get('group_name'),
                post_data.get('blacklist_match'),
                post_data.get('is_relevant', 1),
                post_data.get('scanned_at', datetime.now())
            ))

            conn.commit()
            conn.close()
            return True

        except sqlite3.IntegrityError:
            # הפוסט כבר קיים
            conn.close()
            return False
        except Exception as e:
            conn.close()
            raise Exception(f"שגיאה בשמירת פוסט: {str(e)}")

    def get_last_post_id(self, group_name=None):
        """
        מחזיר את ה-ID של הפוסט האחרון שנסרק

        Args:
            group_name: שם הקבוצה (אופציונלי)

        Returns:
            post_id או None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if group_name:
            cursor.execute('''
                SELECT post_id FROM posts 
                WHERE group_name = ?
                ORDER BY scanned_at DESC 
                LIMIT 1
            ''', (group_name,))
        else:
            cursor.execute('''
                SELECT post_id FROM posts 
                ORDER BY scanned_at DESC 
                LIMIT 1
            ''')

        result = cursor.fetchone()
        conn.close()

        return result[0] if result else None

    def get_all_posts(self, relevant_only=True, limit=100):
        """
        מחזיר רשימת פוסטים

        Args:
            relevant_only: האם להחזיר רק רלוונטיים
            limit: מספר מקסימלי של פוסטים

        Returns:
            רשימת dictionaries
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        if relevant_only:
            cursor.execute('''
                SELECT * FROM posts 
                WHERE is_relevant = 1 
                ORDER BY scanned_at DESC 
                LIMIT ?
            ''', (limit,))
        else:
            cursor.execute('''
                SELECT * FROM posts 
                ORDER BY scanned_at DESC 
                LIMIT ?
            ''', (limit,))

        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()

        # המרה ל-list של dictionaries
        posts = []
        for row in rows:
            posts.append(dict(zip(columns, row)))

        return posts

    def get_stats(self):
        """
        מחזיר סטטיסטיקות על הפוסטים

        Returns:
            dictionary עם סטטיסטיקות
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # סה"כ פוסטים
        cursor.execute('SELECT COUNT(*) FROM posts')
        total = cursor.fetchone()[0]

        # רלוונטיים
        cursor.execute('SELECT COUNT(*) FROM posts WHERE is_relevant = 1')
        relevant = cursor.fetchone()[0]

        # blacklist
        cursor.execute('SELECT COUNT(*) FROM posts WHERE blacklist_match IS NOT NULL')
        blacklisted = cursor.fetchone()[0]

        # היום
        cursor.execute('''
            SELECT COUNT(*) FROM posts 
            WHERE DATE(scanned_at) = DATE('now')
        ''')
        today = cursor.fetchone()[0]

        conn.close()

        return {
            'total': total,
            'relevant': relevant,
            'blacklisted': blacklisted,
            'today': today
        }

    def export_to_csv(self, filename="apartments_export.csv", relevant_only=True):
        """
        מייצא פוסטים ל-CSV

        Args:
            filename: שם הקובץ
            relevant_only: רק רלוונטיים

        Returns:
            True אם הצליח
        """
        import pandas as pd

        posts = self.get_all_posts(relevant_only=relevant_only, limit=10000)

        if not posts:
            return False

        df = pd.DataFrame(posts)

        # סידור עמודות
        columns_order = ['id', 'content', 'post_url', 'author', 'group_name',
                         'blacklist_match', 'scanned_at']
        df = df[columns_order]

        df.to_csv(filename, index=False, encoding='utf-8-sig')
        return True

    def clear_old_posts(self, days=30):
        """
        מוחק פוסטים ישנים

        Args:
            days: כמה ימים לאחור לשמור

        Returns:
            כמה פוסטים נמחקו
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            DELETE FROM posts 
            WHERE scanned_at < datetime('now', '-' || ? || ' days')
        ''', (days,))

        deleted = cursor.rowcount
        conn.commit()
        conn.close()

        return deleted
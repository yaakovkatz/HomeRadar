"""
analytics.py - אנליטיקס וסטטיסטיקות מתקדמות
"""

import sqlite3


class Analytics:
    """מחלקה לחישוב אנליטיקס וטרנדים"""

    def __init__(self, db_path="posts.db"):
        """
        אתחול

        Args:
            db_path: נתיב לדאטאבייס
        """
        self.db_path = db_path

    def get_average_price_today(self):
        """
        מחזיר ממוצע מחירים של דירות היום

        Returns:
            int: ממוצע מחיר, או 0 אם אין נתונים
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT AVG(CAST(price AS INTEGER))
            FROM posts 
            WHERE DATE(scanned_at) = DATE('now')
            AND price IS NOT NULL
            AND is_relevant = 1
        ''')

        result = cursor.fetchone()[0]
        conn.close()

        return int(result) if result else 0

    def get_average_rooms_today(self):
        """
        מחזיר ממוצע חדרים של דירות היום

        Returns:
            float: ממוצע חדרים, או 0 אם אין נתונים
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT AVG(CAST(rooms AS REAL))
            FROM posts 
            WHERE DATE(scanned_at) = DATE('now')
            AND rooms IS NOT NULL
            AND is_relevant = 1
        ''')

        result = cursor.fetchone()[0]
        conn.close()

        return round(result, 1) if result else 0

    def get_popular_city_today(self):
        """
        מחזיר את העיר הכי פופולרית היום

        Returns:
            str: שם העיר + כמות, או "אין נתונים"
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute('''
            SELECT city, COUNT(*) as count
            FROM posts 
            WHERE DATE(scanned_at) = DATE('now')
            AND city IS NOT NULL
            AND is_relevant = 1
            GROUP BY city
            ORDER BY count DESC
            LIMIT 1
        ''')

        result = cursor.fetchone()
        conn.close()

        if result:
            return f"{result[0]} ({result[1]})"
        return "אין נתונים"

    def get_apartments_per_hour_today(self):
        """
        מחזיר ממוצע דירות לשעה היום

        Returns:
            float: ממוצע דירות לשעה
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # כמה דירות היום
        cursor.execute('''
            SELECT COUNT(*)
            FROM posts 
            WHERE DATE(scanned_at) = DATE('now')
            AND is_relevant = 1
        ''')
        count = cursor.fetchone()[0]

        # כמה שעות עברו מתחילת היום
        cursor.execute('''
            SELECT (JULIANDAY('now') - JULIANDAY(DATE('now'))) * 24
        ''')
        hours = cursor.fetchone()[0]

        conn.close()

        if hours > 0:
            return round(count / hours, 1)
        return 0.0

    def get_trends_today(self):
        """
        מחזיר כל הטרנדים של היום במבנה אחד

        Returns:
            dict: {
                'avg_price': int,
                'avg_rooms': float,
                'popular_city': str,
                'apartments_per_hour': float
            }
        """
        return {
            'avg_price': self.get_average_price_today(),
            'avg_rooms': self.get_average_rooms_today(),
            'popular_city': self.get_popular_city_today(),
            'apartments_per_hour': self.get_apartments_per_hour_today()
        }
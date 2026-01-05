"""
database.py - ניהול דאטאבייס SQLite
גרסה סופית ומתוקנת: זיהוי רחובות חכם (ללא סוגריים מיותרים), עוגנים, וללא אימוג'ים בטקסט הרחוב.
"""

import sqlite3
from datetime import datetime
import os
import re

class PostDatabase:
    def __init__(self, db_path="posts.db"):
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                post_url TEXT UNIQUE,
                post_id TEXT,
                content TEXT,
                author TEXT,
                city TEXT,
                price TEXT,
                rooms TEXT,
                phone TEXT,
                group_name TEXT,
                blacklist_match TEXT,
                is_relevant INTEGER DEFAULT 1,
                scanned_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        conn.commit()
        conn.close()

    def save_post(self, post_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            details = self.extract_details(post_data.get('content', ''))
            cursor.execute('''
                           INSERT INTO posts (post_url, post_id, content, author, city, price, rooms, phone,
                                              group_name, blacklist_match, is_relevant, scanned_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                           ''', (
                               post_data.get('post_url'),
                               post_data.get('post_id'),
                               post_data.get('content'),
                               post_data.get('author'),
                               details['city'],
                               details['price'],
                               details['rooms'],
                               details['phone'],
                               post_data.get('group_name'),
                               post_data.get('blacklist_match'),
                               post_data.get('is_relevant', 1),
                               post_data.get('scanned_at', datetime.now())
                           ))
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False
        except Exception as e:
            raise Exception(f"שגיאה בשמירת פוסט: {str(e)}")
        finally:
            conn.close()

    def get_last_post_id(self, group_name=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        if group_name:
            cursor.execute('SELECT post_id FROM posts WHERE group_name = ? ORDER BY scanned_at DESC LIMIT 1', (group_name,))
        else:
            cursor.execute('SELECT post_id FROM posts ORDER BY scanned_at DESC LIMIT 1')
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def get_all_posts(self, relevant_only=True, limit=100):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        sql = 'SELECT * FROM posts '
        if relevant_only:
            sql += 'WHERE is_relevant = 1 '
        sql += 'ORDER BY scanned_at DESC LIMIT ?'
        cursor.execute(sql, (limit,))
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()
        conn.close()
        return [dict(zip(columns, row)) for row in rows]

    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM posts')
        total = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM posts WHERE is_relevant = 1')
        relevant = cursor.fetchone()[0]
        cursor.execute('SELECT COUNT(*) FROM posts WHERE blacklist_match IS NOT NULL')
        blacklisted = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM posts WHERE DATE(scanned_at) = DATE('now')")
        today = cursor.fetchone()[0]
        conn.close()
        return {'total': total, 'relevant': relevant, 'blacklisted': blacklisted, 'today': today}

    def get_week_stats(self): return self._get_period_stats(7)
    def get_month_stats(self): return self._get_period_stats(30)

    def _get_period_stats(self, days):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM posts WHERE DATE(scanned_at) >= DATE('now', '-{days} days') AND is_relevant = 1")
        relevant = cursor.fetchone()[0]
        cursor.execute(f"SELECT COUNT(*) FROM posts WHERE DATE(scanned_at) >= DATE('now', '-{days} days') AND blacklist_match IS NOT NULL")
        blacklisted = cursor.fetchone()[0]
        conn.close()
        return {'relevant': relevant, 'blacklisted': blacklisted}

    def clear_old_posts(self, days=30):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM posts WHERE scanned_at < datetime('now', '-' || ? || ' days')", (days,))
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted

    def export_to_csv(self, filename="apartments_export.csv", relevant_only=True):
        import pandas as pd
        posts = self.get_all_posts(relevant_only=relevant_only, limit=10000)
        if not posts: return False
        df = pd.DataFrame(posts)
        columns_order = ['id', 'content', 'post_url', 'author', 'group_name', 'blacklist_match', 'scanned_at']
        existing_cols = [c for c in columns_order if c in df.columns]
        df = df[existing_cols]
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        return True

    # =================================================================
    #              מנוע החילוץ החכם (לוגיקה משופרת)
    # =================================================================

    def extract_summary(self, content):
        if not content: return ""
        details = self.extract_details(content)
        parts = []
        if details['city']: parts.append(details['city'])
        if details['price']: parts.append(f"{details['price']} ₪")
        if details['rooms']: parts.append(f"{details['rooms']} חד'")

        summary = " | ".join(parts)
        if len(summary) < 5:
            return content.replace('\n', ' ').strip()[:50] + "..."
        return summary

    def extract_details(self, content):
        """
        מחלץ פרטים - גרסה משודרגת (תומכת במעלה אדומים + מחירים עם נקודות)
        """
        if not content:
            return {'city': None, 'price': None, 'rooms': None, 'phone': None}

        details = {'city': None, 'price': None, 'rooms': None, 'phone': None}
        content_clean = content.replace('\n', ' ')

        # --- 1. זיהוי רחוב חכם ---
        street_pattern = r"(?:רחוב|רח'|רח|שדרות|סמטת|דרך)\s+([א-ת\s\"'0-9\(\)]+?)(?=\d{2,}|,|\.|-|–|:|ללא|בקרבת|ליד|קרוב|בין|מתאריך|$)"
        matches = re.finditer(street_pattern, content_clean)
        blacklist_words = ['שקט', 'קטן', 'מבוקש', 'פסטורלי', 'ללא מוצא', 'ראשי', 'הולנדי', 'חד סטרי', 'פנימי', 'משופץ',
                           'מרווח']

        for match in matches:
            raw_candidate = match.group(1)
            clean_candidate = re.sub(r'\(\d+\)', '', raw_candidate)
            candidate = clean_candidate.strip(" ()-.,–:")
            is_blacklisted = any(bad_word in candidate for bad_word in blacklist_words)

            if not is_blacklisted and 2 < len(candidate) < 25 and not candidate.isdigit():
                details['city'] = candidate
                break

        # --- 2. זיהוי שכונה ---
        if not details['city']:
            area_pattern = r"(?:שכונת|בשכונת|איזור|אזור|ליד|בסמוך ל|בלב|במרכז)\s+([א-ת\s\"']+?)(?=\d|,|\.|-|–|:|ללא|שקט|מבוקש|בין|$)"
            area_match = re.search(area_pattern, content_clean)
            if area_match:
                raw_val = area_match.group(1)
                clean_val = re.sub(r'\(\d+\)', '', raw_val)
                val = clean_val.strip(" ()-.,–:")
                if 2 < len(val) < 25:
                    details['city'] = val

        # --- 3. זיהוי עוגנים ---
        if not details['city']:
            landmarks = {
                'שוק מחנה יהודה': 'ירושלים (נחלאות)',
                'הכותל': 'ירושלים (העתיקה)',
                'מכון ויצמן': 'רחובות',
                'סורוקה': 'באר שבע',
                'האוניברסיטה': 'באר שבע (אונ\')',
                'עזריאלי': 'תל אביב',
                'שרונה': 'תל אביב',
                'בצלאל': 'ירושלים',
                'הטכניון': 'חיפה'
            }
            for landmark, location in landmarks.items():
                if landmark in content:
                    details['city'] = location
                    break

        # --- 4. זיהוי עיר (רשימה מורחבת!) ---
        if not details['city']:
            # הוספתי את מעלה אדומים ועוד כמה נפוצות
            cities = [
                'תל אביב', 'תל-אביב', 'ירושלים', 'חיפה', 'רחובות',
                'נס ציונה', 'נס-ציונה', 'ראשון לציון', 'ראשל"צ',
                'פתח תקווה', 'פתח-תקווה', 'פ"ת', 'נתניה', 'באר שבע',
                'באר-שבע', 'בני ברק', 'בני-ברק', 'רמת גן', 'רמת-גן',
                'חולון', 'אשדוד', 'אשקלון', 'הרצליה', 'כפר סבא',
                'רעננה', 'מודיעין', 'בת ים', 'בת-ים', 'גבעתיים',
                'מעלה אדומים', 'בית שמש', 'לוד', 'רמלה', 'קרית גת',
                'עפולה', 'נהריה', 'עכו', 'טבריה', 'אילת'
            ]
            for city in cities:
                if city in content:
                    clean_city = city.replace('-', ' ').replace('"', '')
                    details['city'] = clean_city
                    break

        # --- 5. מחיר (מנגנון כפול ומשופר) ---

        # ניסיון א': חיפוש רגיל עם ש"ח (תומך גם בנקודות וגם בפסיקים)
        # דוגמה: 3,000,000 ש"ח או 3.000.000 ₪
        price_pattern_1 = r'(\d{1,3}(?:[,\.]\d{3})+)\s*(?:₪|ש"ח|שח)'
        price_match = re.search(price_pattern_1, content)

        # ניסיון ב': אם לא מצאנו, נחפש את המילה "מחיר" לפני המספר
        # דוגמה: מחיר: 3.180.000
        if not price_match:
            price_pattern_2 = r'(?:מחיר|במחיר)\s*[:\-]?\s*(\d{1,3}(?:[,\.]\d{3})+)'
            price_match = re.search(price_pattern_2, content)

        if price_match:
            try:
                # מנקים גם פסיקים וגם נקודות כדי להפוך למספר
                clean_price = price_match.group(1).replace(',', '').replace('.', '')
                if 1000 <= int(clean_price) <= 50000000:
                    details['price'] = clean_price
            except:
                pass

        # --- טלפון ---
        phone_match = re.search(r'0\d{1,2}[-\s]?\d{3}[-\s]?\d{4}', content)
        if phone_match:
            details['phone'] = phone_match.group(0).replace(' ', '').replace('-', '')

        # --- חדרים ---
        rooms_match = re.search(r'(\d+\.?\d*)\s*חדר', content)
        if rooms_match:
            details['rooms'] = rooms_match.group(1)

        return details
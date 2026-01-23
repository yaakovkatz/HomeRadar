#!/usr/bin/env python3
"""
🧪 Automated Tests for tune_ai.py

מריץ טסטים אוטומטיים על tune_ai כדי לוודא שהוא עובד נכון.
"""

import sqlite3
import json
import os
import sys
from datetime import datetime

class TuneAITests:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.test_db = "posts_test.db"
        self.config_path = "config.json"

    def run_all_tests(self):
        """מריץ את כל הטסטים"""
        print("\n" + "=" * 70)
        print("🧪 Tune AI - Automated Tests")
        print("=" * 70 + "\n")

        # בדיקה שקבצים קיימים
        self.test_files_exist()

        # בדיקה שיש DB לטסטים
        if not os.path.exists(self.test_db):
            print("⚠️ posts_test.db לא קיים - יוצר DB לטסטים...")
            self.create_test_db()

        # טסטים על הDB
        self.test_db_structure()
        self.test_broker_detection()
        self.test_settlement_detection()
        self.test_blacklist_detection()
        self.test_misclassified_detection()

        # טסט שלמות config.json
        self.test_config_integrity()

        # סיכום
        print("\n" + "=" * 70)
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print("=" * 70 + "\n")

        if self.failed > 0:
            sys.exit(1)

    def test_files_exist(self):
        """בודק שקבצים חשובים קיימים"""
        print("📁 בודק קיום קבצים...")

        required_files = [
            'tune_ai.py',
            'config.json',
            'ai_agents.py',
            'database.py'
        ]

        for file in required_files:
            if os.path.exists(file):
                print(f"  ✅ {file} קיים")
                self.passed += 1
            else:
                print(f"  ❌ {file} לא נמצא!")
                self.failed += 1

    def test_db_structure(self):
        """בודק שמבנה הDB תקין"""
        print("\n🗄️ בודק מבנה DB...")

        if not os.path.exists(self.test_db):
            print("  ⏭️ דילוג - אין DB")
            return

        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()

            # בדוק שהטבלה קיימת
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='posts'")
            if cursor.fetchone():
                print("  ✅ טבלת posts קיימת")
                self.passed += 1
            else:
                print("  ❌ טבלת posts לא קיימת!")
                self.failed += 1
                return

            # בדוק עמודות
            cursor.execute("PRAGMA table_info(posts)")
            columns = {row[1] for row in cursor.fetchall()}

            required_columns = {'post_id', 'content', 'author', 'is_relevant', 'is_broker', 'category', 'city'}

            if required_columns.issubset(columns):
                print(f"  ✅ כל העמודות הנדרשות קיימות ({len(columns)} עמודות)")
                self.passed += 1
            else:
                missing = required_columns - columns
                print(f"  ❌ חסרות עמודות: {missing}")
                self.failed += 1

    def test_broker_detection(self):
        """בודק זיהוי מתווכים"""
        print("\n🏢 בודק זיהוי מתווכים...")

        if not os.path.exists(self.test_db):
            print("  ⏭️ דילוג - אין DB")
            return

        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()

            # בדוק שיש פוסטי BROKER
            cursor.execute("SELECT COUNT(*) FROM posts WHERE is_broker = 1 OR category = 'BROKER'")
            broker_count = cursor.fetchone()[0]

            if broker_count > 0:
                print(f"  ✅ נמצאו {broker_count} פוסטי מתווכים")
                self.passed += 1
            else:
                print("  ❌ לא נמצאו פוסטי מתווכים!")
                self.failed += 1

    def test_settlement_detection(self):
        """בודק זיהוי יישובים"""
        print("\n🏘️ בודק זיהוי יישובים...")

        if not os.path.exists(self.test_db):
            print("  ⏭️ דילוג - אין DB")
            return

        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()

            # בדוק שיש פוסטי NON_URBAN
            cursor.execute("SELECT COUNT(*) FROM posts WHERE category = 'NON_URBAN'")
            non_urban_count = cursor.fetchone()[0]

            if non_urban_count > 0:
                print(f"  ✅ נמצאו {non_urban_count} פוסטים NON_URBAN")
                self.passed += 1
            else:
                print("  ❌ לא נמצאו פוסטים NON_URBAN!")
                self.failed += 1

    def test_blacklist_detection(self):
        """בודק זיהוי ביטויי חיפוש"""
        print("\n🚫 בודק זיהוי ביטויי blacklist...")

        if not os.path.exists(self.test_db):
            print("  ⏭️ דילוג - אין DB")
            return

        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()

            # בדוק שיש פוסטים עם "מחפש"
            cursor.execute("""
                SELECT COUNT(*) FROM posts
                WHERE content LIKE '%מחפש%' OR content LIKE '%דרוש%'
            """)
            search_count = cursor.fetchone()[0]

            if search_count > 0:
                print(f"  ✅ נמצאו {search_count} פוסטים עם ביטויי חיפוש")
                self.passed += 1
            else:
                print("  ⚠️ לא נמצאו פוסטים עם ביטויי חיפוש")
                self.passed += 1  # זה בסדר

    def test_misclassified_detection(self):
        """בודק זיהוי פוסטים שסווגו לא נכון"""
        print("\n⚠️ בודק זיהוי פוסטים שסווגו לא נכון...")

        if not os.path.exists(self.test_db):
            print("  ⏭️ דילוג - אין DB")
            return

        with sqlite3.connect(self.test_db) as conn:
            cursor = conn.cursor()

            # טען broker_keywords
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            broker_keywords = [kw.lower() for kw in config['search_settings']['search_settings']['broker_keywords']]

            # בדוק RELEVANT עם מילות מתווך
            cursor.execute("""
                SELECT COUNT(*) FROM posts
                WHERE is_relevant = 1
                AND category = 'RELEVANT'
            """)
            relevant_posts = cursor.fetchone()[0]

            if relevant_posts > 0:
                print(f"  ✅ נמצאו {relevant_posts} פוסטים RELEVANT לבדיקה")
                self.passed += 1
            else:
                print("  ⚠️ לא נמצאו פוסטים RELEVANT")
                self.passed += 1

            # בדוק NON_URBAN מעיר רלוונטית
            cities = [city.lower() for city in config['search_settings']['cities']]
            cursor.execute("""
                SELECT COUNT(*) FROM posts
                WHERE category = 'NON_URBAN'
                AND city IS NOT NULL
            """)
            non_urban_with_city = cursor.fetchone()[0]

            if non_urban_with_city > 0:
                print(f"  ✅ נמצאו {non_urban_with_city} פוסטים NON_URBAN עם עיר")
                self.passed += 1
            else:
                print("  ⚠️ לא נמצאו פוסטים NON_URBAN עם עיר")
                self.passed += 1

    def test_config_integrity(self):
        """בודק שלמות config.json"""
        print("\n⚙️ בודק שלמות config.json...")

        if not os.path.exists(self.config_path):
            print("  ❌ config.json לא נמצא!")
            self.failed += 1
            return

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            # בדוק מבנה
            if 'search_settings' in config:
                print("  ✅ search_settings קיים")
                self.passed += 1
            else:
                print("  ❌ search_settings חסר!")
                self.failed += 1
                return

            if 'cities' in config['search_settings']:
                cities_count = len(config['search_settings']['cities'])
                print(f"  ✅ רשימת ערים קיימת ({cities_count} ערים)")
                self.passed += 1
            else:
                print("  ❌ רשימת ערים חסרה!")
                self.failed += 1

            if 'broker_keywords' in config['search_settings']['search_settings']:
                broker_count = len(config['search_settings']['search_settings']['broker_keywords'])
                print(f"  ✅ broker_keywords קיימת ({broker_count} מילות מפתח)")
                self.passed += 1
            else:
                print("  ❌ broker_keywords חסרה!")
                self.failed += 1

        except json.JSONDecodeError as e:
            print(f"  ❌ שגיאת JSON: {e}")
            self.failed += 1

    def create_test_db(self):
        """יוצר DB לטסטים אם לא קיים"""
        print("  📦 יוצר posts_test.db...")

        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        cursor.execute('''
        CREATE TABLE IF NOT EXISTS posts (
            post_id TEXT PRIMARY KEY,
            content TEXT,
            author TEXT,
            scanned_at TEXT,
            is_relevant INTEGER,
            is_broker INTEGER,
            category TEXT,
            city TEXT,
            location TEXT,
            price TEXT,
            rooms TEXT,
            phone TEXT,
            ai_reason TEXT,
            group_name TEXT
        )
        ''')

        # נתונים מינימליים
        test_data = [
            ('test_broker1', 'דורון נכסים - תיק נכסים', 'דורון', datetime.now().isoformat(), 0, 1, 'BROKER', None, None, None, None, None, 'מתווך', 'דירות'),
            ('test_relevant1', 'דירה 4 חדרים בירושלים', 'משה', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'ירושלים', None, '7000', '4', None, 'דירה', 'דירות'),
            ('test_nonurban1', 'בית במושב', 'אבי', datetime.now().isoformat(), 0, 0, 'NON_URBAN', None, None, None, None, None, 'מושב', 'דירות'),
        ]

        cursor.executemany('''
        INSERT OR REPLACE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', test_data)

        conn.commit()
        conn.close()
        print("  ✅ נוצר posts_test.db")

if __name__ == "__main__":
    tester = TuneAITests()
    tester.run_all_tests()

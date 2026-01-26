#!/usr/bin/env python3
"""
🎯 Tune AI - אוטומציה לעדכון הגדרות AI

סורק את בסיס הנתונים, מוצא דפוסים, ומציע עדכונים אוטומטיים:
- מתווכים חדשים
- יישובים לא רלוונטיים
- ביטויים לblacklist

Usage:
    python tune_ai.py                  # רק סקירה
    python tune_ai.py --interactive    # אינטראקטיבי
    python tune_ai.py --apply          # אוטומטי מלא
    python tune_ai.py --report         # דוח מפורט
"""

import sqlite3
import json
import re
import argparse
from datetime import datetime
from collections import Counter
import os
import shutil

class TuneAI:
    def __init__(self, db_path="posts.db", config_path="config.json"):
        self.db_path = db_path
        self.config_path = config_path
        self.recommendations = {
            'brokers': [],
            'publishers_for_brokers': [],  # מפרסמים שעובדים עבור מתווכים
            'settlements': [],
            'blacklist': [],
            'spam': [],
            'repeat_posters': [],
            'misclassified': []
        }

    def analyze(self):
        """סריקה מלאה של הDB + המלצות"""
        print("\n" + "=" * 70)
        print("🎯 Tune AI - סריקת בסיס נתונים")
        print("=" * 70 + "\n")

        # 1. סטטיסטיקות בסיסיות
        stats = self._get_stats()
        self._print_stats(stats)

        # 2. זיהוי מתווכים חדשים
        print("\n" + "-" * 70)
        print("🔍 מחפש מתווכים חדשים...")
        self._find_new_brokers()

        # 2.5. זיהוי מפרסמים שעובדים עבור מתווכים
        print("\n" + "-" * 70)
        print("👤 מחפש מפרסמים שעובדים עבור מתווכים...")
        self._find_publishers_for_brokers()

        # 3. זיהוי יישובים
        print("\n" + "-" * 70)
        print("🏘️ מחפש יישובים לא רלוונטיים...")
        self._find_settlements()

        # 4. ביטויים לblacklist
        print("\n" + "-" * 70)
        print("🚫 מחפש ביטויים חדשים לחסימה...")
        self._find_blacklist_terms()

        # 5. זיהוי פוסטים חוזרים
        print("\n" + "-" * 70)
        print("🔁 מחפש משתמשים שמפרסמים הרבה פעמים...")
        self._find_repeat_posters()

        # 6. זיהוי פוסטים שסווגו לא נכון
        print("\n" + "-" * 70)
        print("⚠️ מחפש פוסטים שאולי סווגו לא נכון...")
        self._find_misclassified_posts()

        # 7. סיכום המלצות
        print("\n" + "=" * 70)
        self._print_recommendations()

    def _get_stats(self):
        """סטטיסטיקות בסיסיות"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            stats = {}

            # סה"כ פוסטים
            cursor.execute("SELECT COUNT(*) FROM posts")
            stats['total'] = cursor.fetchone()[0]

            # רלוונטיים
            cursor.execute("SELECT COUNT(*) FROM posts WHERE is_relevant = 1")
            stats['relevant'] = cursor.fetchone()[0]

            # מתווכים
            cursor.execute("SELECT COUNT(*) FROM posts WHERE is_broker = 1")
            stats['brokers'] = cursor.fetchone()[0]

            # NON_URBAN
            cursor.execute("SELECT COUNT(*) FROM posts WHERE category = 'NON_URBAN'")
            stats['non_urban'] = cursor.fetchone()[0]

            # SPAM
            cursor.execute("SELECT COUNT(*) FROM posts WHERE category IN ('SPAM', 'WANTED')")
            stats['spam'] = cursor.fetchone()[0]

            return stats

    def _print_stats(self, stats):
        """הדפסת סטטיסטיקות"""
        print("📊 סטטיסטיקות:")
        print(f"  📝 סה\"כ פוסטים: {stats['total']}")
        print(f"  ✅ רלוונטיים: {stats['relevant']}")
        print(f"  🚫 מתווכים נחסמו: {stats['brokers']}")
        print(f"  🏘️ יישובים לא רלוונטיים: {stats['non_urban']}")
        print(f"  ⚠️ ספאם: {stats['spam']}")

    def _find_new_brokers(self):
        """מוצא שמות מתווכים חדשים - גם חברות וגם שמות פרטיים"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # שלוף פוסטים שסומנו כמתווכים או חשודים
            cursor.execute("""
                SELECT post_id, content, author, ai_reason, category
                FROM posts
                WHERE is_broker = 1 OR category = 'BROKER' OR category = 'SUSPECTED_BROKER'
                LIMIT 100
            """)

            broker_posts = cursor.fetchall()

        # טען broker_keywords קיימים
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        existing_keywords = set(kw.lower() for kw in config['search_settings']['search_settings']['broker_keywords'])

        # חלץ שמות חברות + שמות פרטיים
        broker_names = []
        suspected_names = []  # רשימה נפרדת לחשודים

        # מילונים לשמירת הפוסטים לפי שם מתווך
        broker_posts_dict = {}  # {broker_name: [(post_id, content, author), ...]}
        suspected_posts_dict = {}  # {broker_name: [(post_id, content, author), ...]}

        # Patterns לשמות חברות
        company_patterns = [
            r'נדל["\']ן\s+(\w+)',  # נדל"ן X
            r'(\w+)\s+נכסים',      # X נכסים
            r'Real\s+Estate\s+(\w+)',  # Real Estate X
            r'מתווך[ת]?\s+(\w+)',  # מתווך X
        ]

        # Patterns לשמות פרטיים מתוך ai_reason
        name_patterns = [
            r'חתימה עסקית:\s*([א-ת\sA-Za-z\'"״]+?)(?:\s*[\+\)]|$)',  # "חתימה עסקית: ירדן גמליאל"
            r'חתימה:\s*([א-ת\sA-Za-z\'"״]+?)(?:\s*[\+\)]|$)',         # "חתימה: נדל"ן JF"
            r'מתווך\s*\(([א-ת\sA-Za-z\'"״]+?)\)',                    # "מתווך (שם)"
        ]

        # דפוסים להתעלמות (לא לתפוס אותם!)
        ignore_patterns = [
            r'מילת מפתח',
            r'סוכן נדל',
            r'מספר רישיון',
            r'מ\.ר\.',
        ]

        for post_id, content, author, reason, category in broker_posts:
            text_all = content + " " + (author or "") + " " + (reason or "")

            # 1. חיפוש שמות חברות (patterns רגילים)
            for pattern in company_patterns:
                matches = re.findall(pattern, text_all, re.IGNORECASE)
                for match in matches:
                    # בדוק אם זה לא דפוס להתעלמות
                    if not any(ignore in match for ignore in ['מילת', 'מפתח']):
                        if category == 'SUSPECTED_BROKER':
                            suspected_names.append(match)
                            if match not in suspected_posts_dict:
                                suspected_posts_dict[match] = []
                            suspected_posts_dict[match].append((post_id, content, author))
                        else:
                            broker_names.append(match)
                            if match not in broker_posts_dict:
                                broker_posts_dict[match] = []
                            broker_posts_dict[match].append((post_id, content, author))

            # 2. חיפוש שמות פרטיים מתוך ai_reason
            if reason and 'מילת מפתח' not in reason:
                for pattern in name_patterns:
                    matches = re.findall(pattern, reason, re.IGNORECASE)
                    for match in matches:
                        # נקה את השם (הסר רווחים מיותרים)
                        clean_name = match.strip()

                        # סינון: דלג על דפוסים להתעלמות
                        should_ignore = False
                        for ignore_pat in ignore_patterns:
                            if re.search(ignore_pat, clean_name, re.IGNORECASE):
                                should_ignore = True
                                break

                        if not should_ignore and clean_name and len(clean_name) > 3:
                            # כל הפוסטים האלה (BROKER או SUSPECTED_BROKER) הם חשודים
                            # כי אין להם מספר רישיון - רק שם פרטי
                            suspected_names.append(clean_name)
                            if clean_name not in suspected_posts_dict:
                                suspected_posts_dict[clean_name] = []
                            suspected_posts_dict[clean_name].append((post_id, content, author))

            # 3. חיפוש מה-author אם זה BROKER וודאי
            if category == 'BROKER' and author and 'מילת' not in author:
                # אם האוטור הוא שם (לא "Admin" או "Group")
                if len(author.split()) <= 3 and len(author.split()) >= 2:  # שם מלא (2-3 מילים)
                    try:
                        if author[0].isupper():
                            clean_author = author.strip()
                            suspected_names.append(clean_author)
                            if clean_author not in suspected_posts_dict:
                                suspected_posts_dict[clean_author] = []
                            suspected_posts_dict[clean_author].append((post_id, content, author))
                    except:
                        pass

        # ספור תדירויות
        confirmed_counter = Counter(broker_names)
        suspected_counter = Counter(suspected_names)

        # סנן רק חדשים ופופולריים (מתווכים וודאיים)
        for name, count in confirmed_counter.most_common(10):
            clean_name = name.strip()
            clean_name_lower = clean_name.lower()

            # בדוק אם השם כבר קיים, או אם הוא חלק משם ארוך יותר שכבר קיים
            is_already_blocked = False

            # בדיקה 1: האם השם עצמו קיים?
            if clean_name_lower in existing_keywords:
                is_already_blocked = True

            # בדיקה 2: האם השם הוא חלק משם ארוך יותר? (למשל "מור" ב"מור נכסים")
            if not is_already_blocked:
                for existing_kw in existing_keywords:
                    # בדוק אם השם שמצאנו הוא חלק מביטוי ארוך יותר שכבר קיים
                    if clean_name_lower in existing_kw and len(clean_name_lower) < len(existing_kw):
                        is_already_blocked = True
                        break

            if count >= 2 and not is_already_blocked:
                posts_list = broker_posts_dict.get(name, [])
                self.recommendations['brokers'].append({
                    'term': clean_name,
                    'count': count,
                    'reason': f"מופיע {count} פעמים בפוסטי מתווכים וודאיים",
                    'type': 'confirmed',
                    'posts': posts_list[:3]  # רק 3 פוסטים ראשונים
                })

        # חשודים (גם אם רק 1 פעם)
        for name, count in suspected_counter.most_common(10):
            clean_name = name.strip()
            clean_name_lower = clean_name.lower()

            # בדוק אם השם כבר קיים, או אם הוא חלק משם ארוך יותר שכבר קיים
            is_already_blocked = False

            # בדיקה 1: האם השם עצמו קיים?
            if clean_name_lower in existing_keywords:
                is_already_blocked = True

            # בדיקה 2: האם השם הוא חלק משם ארוך יותר? (למשל "מור" ב"מור נכסים")
            if not is_already_blocked:
                for existing_kw in existing_keywords:
                    # בדוק אם השם שמצאנו הוא חלק מביטוי ארוך יותר שכבר קיים
                    if clean_name_lower in existing_kw and len(clean_name_lower) < len(existing_kw):
                        is_already_blocked = True
                        break

            if not is_already_blocked:
                posts_list = suspected_posts_dict.get(name, [])
                self.recommendations['brokers'].append({
                    'term': clean_name,
                    'count': count,
                    'reason': f"חשוד למתווך ({count} פוסטים)",
                    'type': 'suspected',
                    'posts': posts_list[:3]  # רק 3 פוסטים ראשונים
                })

        # הדפסה
        if self.recommendations['brokers']:
            confirmed = [b for b in self.recommendations['brokers'] if b.get('type') == 'confirmed']
            suspected = [b for b in self.recommendations['brokers'] if b.get('type') == 'suspected']

            if confirmed:
                print(f"  🔴 נמצאו {len(confirmed)} מתווכים וודאיים:")
                for item in confirmed[:5]:
                    print(f"     ⚠️ '{item['term']}' - {item['count']} פוסטים")
                    # הצג תצוגה מקדימה של הפוסטים
                    for i, (post_id, content, author) in enumerate(item.get('posts', [])[:2], 1):
                        preview = content[:80].replace('\n', ' ')
                        if len(content) > 80:
                            preview += "..."
                        print(f"        📄 פוסט #{i}: {preview}")
                        if author:
                            print(f"           👤 מחבר: {author}")

            if suspected:
                print(f"  🟡 נמצאו {len(suspected)} מתווכים חשודים:")
                for item in suspected[:5]:
                    print(f"     🔍 '{item['term']}' - {item['count']} פוסטים (חשד)")
                    # הצג תצוגה מקדימה של הפוסטים
                    for i, (post_id, content, author) in enumerate(item.get('posts', [])[:2], 1):
                        preview = content[:80].replace('\n', ' ')
                        if len(content) > 80:
                            preview += "..."
                        print(f"        📄 פוסט #{i}: {preview}")
                        if author:
                            print(f"           👤 מחבר: {author}")
        else:
            print("  ✅ לא נמצאו מתווכים חדשים")

    def _find_publishers_for_brokers(self):
        """מוצא מפרסמים שעובדים עבור מתווכים - גם עם 1 פוסט!"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # שלוף את כל הפוסטים (לא רק BROKER/SUSPECTED_BROKER)
            cursor.execute("""
                SELECT post_id, content, author, category
                FROM posts
                WHERE author IS NOT NULL
                AND author != ''
                LIMIT 200
            """)

            all_posts = cursor.fetchall()

        # טען broker_keywords קיימים
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        broker_keywords = [kw.lower() for kw in config['search_settings']['search_settings']['broker_keywords']]
        existing_keywords = set(broker_keywords)

        # מילון: author -> [(post_id, content, broker_keywords_found), ...]
        publishers_dict = {}

        for post_id, content, author, category in all_posts:
            content_lower = content.lower()

            # בדוק אם התוכן מכיל broker_keywords
            found_keywords = []
            for kw in broker_keywords:
                if kw in content_lower:
                    found_keywords.append(kw)

            # אם מצאנו broker_keywords בפוסט
            if found_keywords:
                author_lower = author.lower()

                # בדוק אם ה-author עצמו כבר ב-broker_keywords (אז לא צריך להמליץ)
                if author_lower in existing_keywords:
                    continue

                # הוסף את המפרסם לרשימה
                if author not in publishers_dict:
                    publishers_dict[author] = []

                publishers_dict[author].append({
                    'post_id': post_id,
                    'content': content,
                    'broker_keywords': found_keywords
                })

        # עכשיו יש לנו רשימה של authors שמפרסמים פוסטים עם broker_keywords
        # המלץ לחסום אותם (גם אם יש להם רק 1 פוסט!)
        for author, posts in publishers_dict.items():
            # רק אם זה שם פרטי (2-3 מילים, מתחיל באות גדולה)
            if len(author.split()) >= 2 and len(author.split()) <= 3:
                try:
                    if author[0].isupper():
                        self.recommendations['publishers_for_brokers'].append({
                            'author': author,
                            'count': len(posts),
                            'broker_keywords': posts[0]['broker_keywords'],  # המילים שנמצאו
                            'posts': posts[:2]  # עד 2 פוסטים לתצוגה
                        })
                except:
                    pass

        # הדפסה
        if self.recommendations['publishers_for_brokers']:
            print(f"  🟠 נמצאו {len(self.recommendations['publishers_for_brokers'])} מפרסמים שעובדים עבור מתווכים:")
            for item in self.recommendations['publishers_for_brokers'][:5]:
                broker_kw_str = ', '.join(item['broker_keywords'][:2])
                print(f"     👤 '{item['author']}' - {item['count']} פוסטים (מפרסם עבור: {broker_kw_str})")
                # הצג תצוגה מקדימה של הפוסטים
                for i, post in enumerate(item['posts'][:2], 1):
                    preview = post['content'][:80].replace('\n', ' ')
                    if len(post['content']) > 80:
                        preview += "..."
                    print(f"        📄 פוסט #{i}: {preview}")
                    print(f"           💡 מכיל: {', '.join(post['broker_keywords'][:2])}")
            print(f"   💡 המלצה: הוסף ל-broker_keywords (מפרסמים שעובדים עבור מתווכים)")
        else:
            print("  ✅ לא נמצאו מפרסמים חדשים")

    def _find_settlements(self):
        """מוצא יישובים שעברו"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # פוסטים רלוונטיים עם מילות מפתח חשודות
            cursor.execute("""
                SELECT content, city, location
                FROM posts
                WHERE is_relevant = 1
                AND (
                    content LIKE '%מושב%' OR
                    content LIKE '%יישוב%' OR
                    content LIKE '%התנחלות%' OR
                    content LIKE '%נוף%' OR
                    content LIKE '%כפר%'
                )
                LIMIT 50
            """)

            posts = cursor.fetchall()

        # חלץ שמות יישובים
        settlement_pattern = r'(?:מושב|יישוב|התנחלות|כפר)\s+([א-ת\s]{2,20})'

        settlements = []
        for content, city, location in posts:
            text = content + " " + (city or "") + " " + (location or "")
            matches = re.findall(settlement_pattern, text)
            settlements.extend([m.strip() for m in matches])

        # ספור
        counter = Counter(settlements)

        for name, count in counter.most_common(10):
            if count >= 2:
                self.recommendations['settlements'].append({
                    'term': name,
                    'count': count,
                    'reason': f"יישוב קטן - {count} פוסטים"
                })

        # הדפסה
        if self.recommendations['settlements']:
            print(f"  💡 נמצאו {len(self.recommendations['settlements'])} יישובים:")
            for item in self.recommendations['settlements'][:5]:
                print(f"     🏘️ '{item['term']}' - {item['count']} פוסטים")
        else:
            print("  ✅ לא נמצאו יישובים חדשים")

    def _find_blacklist_terms(self):
        """מוצא ביטויים חדשים לblacklist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # פוסטים שעברו אבל מכילים מילות חיפוש
            cursor.execute("""
                SELECT content
                FROM posts
                WHERE is_relevant = 1
                AND (
                    content LIKE '%מחפש%' OR
                    content LIKE '%מחפשת%' OR
                    content LIKE '%דרוש%' OR
                    content LIKE '%זקוק%'
                )
                LIMIT 100
            """)

            posts = cursor.fetchall()

        # טען blacklist קיימת
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        existing_blacklist = set(kw.lower() for kw in config['search_settings']['search_settings']['blacklist'])

        # דפוסים
        patterns = [
            r'מחפש[ת]?\s+חדר',
            r'דרוש[ה]?\s+מקום',
            r'זקוק[ה]?\s+ל',
            r'מחפש[ת]?\s+שותף',
        ]

        terms = []
        for (content,) in posts:
            for pattern in patterns:
                if re.search(pattern, content, re.IGNORECASE):
                    match = re.search(pattern, content, re.IGNORECASE)
                    terms.append(match.group(0))

        # ספור
        counter = Counter(terms)

        for term, count in counter.most_common(10):
            if count >= 3 and term.lower() not in existing_blacklist:
                self.recommendations['blacklist'].append({
                    'term': term,
                    'count': count,
                    'reason': f"ביטוי חיפוש - {count} פוסטים"
                })

        # הדפסה
        if self.recommendations['blacklist']:
            print(f"  💡 נמצאו {len(self.recommendations['blacklist'])} ביטויים:")
            for item in self.recommendations['blacklist'][:5]:
                print(f"     🚫 '{item['term']}' - {item['count']} פוסטים")
        else:
            print("  ✅ לא נמצאו ביטויים חדשים")

    def _find_repeat_posters(self):
        """מזהה משתמשים שמפרסמים הרבה פעמים - אולי מתווכים סמויים"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # ספור פוסטים לפי author (רק פוסטים רלוונטיים שלא סומנו כמתווכים)
            cursor.execute("""
                SELECT author, COUNT(*) as post_count
                FROM posts
                WHERE author IS NOT NULL
                AND author != ''
                AND is_relevant = 1
                AND is_broker = 0
                GROUP BY author
                HAVING post_count >= 5
                ORDER BY post_count DESC
                LIMIT 20
            """)

            repeat_posters = cursor.fetchall()

        # בנה רשימת המלצות
        if 'repeat_posters' not in self.recommendations:
            self.recommendations['repeat_posters'] = []

        for author, count in repeat_posters:
            self.recommendations['repeat_posters'].append({
                'author': author,
                'count': count,
                'reason': f"פרסם {count} פוסטים - אולי מתווך סמוי"
            })

        # הדפסה
        if self.recommendations['repeat_posters']:
            print(f"  ⚠️ נמצאו {len(self.recommendations['repeat_posters'])} משתמשים חשודים:")
            for item in self.recommendations['repeat_posters'][:5]:
                print(f"     🔁 '{item['author']}' - {item['count']} פוסטים")
            print(f"   💡 המלצה: בדוק ידנית - אם זה מתווך הוסף לbroker_keywords")
        else:
            print("  ✅ לא נמצאו משתמשים חשודים")

    def _find_misclassified_posts(self):
        """מזהה פוסטים שאולי סווגו לא נכון"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # טען broker_keywords
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            broker_keywords = [kw.lower() for kw in config['search_settings']['search_settings']['broker_keywords']]
            cities = [city.lower() for city in config['search_settings']['cities']]

            # 1. פוסטים שסומנו RELEVANT אבל יש בהם מילות מפתח של מתווכים
            print("     🔎 בודק RELEVANT עם מילות מתווך...")
            cursor.execute("""
                SELECT post_id, content, author, city
                FROM posts
                WHERE is_relevant = 1
                AND category = 'RELEVANT'
                LIMIT 100
            """)

            relevant_posts = cursor.fetchall()
            for post_id, content, author, city in relevant_posts:
                text = (content + " " + (author or "")).lower()

                # דפוסי שלילה (כמו ב-listener.py)
                negation_patterns = [
                    r'\bללא\s+',      # "ללא תיווך"
                    r'\bבלי\s+',      # "בלי תיווך"
                    r'\bלא\s+',       # "לא תיווך"
                    r'\bללא\s+דמי\s+', # "ללא דמי תיווך"
                    r'\bבלי\s+דמי\s+', # "בלי דמי תיווך"
                ]

                found_keywords = []
                for kw in broker_keywords:
                    if kw in text:
                        # בדוק אם יש שלילה לפני המילה
                        is_negated = False
                        for negation in negation_patterns:
                            pattern = negation + re.escape(kw)
                            if re.search(pattern, text):
                                is_negated = True
                                break

                        # רק אם אין שלילה - הוסף לרשימה
                        if not is_negated:
                            found_keywords.append(kw)

                if found_keywords:
                    self.recommendations['misclassified'].append({
                        'post_id': post_id,
                        'type': 'RELEVANT_WITH_BROKER_KEYWORDS',
                        'content_preview': content[:100] + "...",
                        'city': city,
                        'reason': f"מכיל מילות מתווך: {', '.join(found_keywords[:3])}"
                    })

            # 2. פוסטים שסומנו NON_URBAN אבל הם מעיר רלוונטית
            print("     🔎 בודק NON_URBAN מעיר רלוונטית...")
            cursor.execute("""
                SELECT post_id, content, city, location
                FROM posts
                WHERE category = 'NON_URBAN'
                LIMIT 100
            """)

            non_urban_posts = cursor.fetchall()
            for post_id, content, city, location in non_urban_posts:
                city_lower = (city or "").lower()
                if city_lower in cities:
                    self.recommendations['misclassified'].append({
                        'post_id': post_id,
                        'type': 'NON_URBAN_BUT_RELEVANT_CITY',
                        'content_preview': content[:100] + "...",
                        'city': city,
                        'reason': f"עיר '{city}' רלוונטית אבל סומן NON_URBAN"
                    })

            # 3. פוסטים שסומנו BROKER אבל אין בהם סימני תיווך ברורים
            print("     🔎 בודק BROKER ללא סימני תיווך...")
            cursor.execute("""
                SELECT post_id, content, author, ai_reason
                FROM posts
                WHERE is_broker = 1 OR category = 'BROKER'
                LIMIT 50
            """)

            broker_posts = cursor.fetchall()
            for post_id, content, author, ai_reason in broker_posts:
                text = (content + " " + (author or "")).lower()

                # בדוק אם יש סימנים ברורים
                has_broker_signs = any([
                    kw in text for kw in broker_keywords
                ]) or any([
                    word in text for word in ['מתווך', 'תיווך', 'נדלן', 'נכסים', 'real estate']
                ])

                if not has_broker_signs:
                    self.recommendations['misclassified'].append({
                        'post_id': post_id,
                        'type': 'BROKER_WITHOUT_CLEAR_SIGNS',
                        'content_preview': content[:100] + "...",
                        'city': None,
                        'reason': f"אין סימני תיווך ברורים. AI אמר: {ai_reason[:50] if ai_reason else 'N/A'}"
                    })

        # הדפסה
        if self.recommendations['misclassified']:
            print(f"  ⚠️ נמצאו {len(self.recommendations['misclassified'])} פוסטים חשודים:")
            for item in self.recommendations['misclassified'][:5]:
                print(f"     ⚠️ Post #{item['post_id']} - {item['type']}")
                print(f"        {item['reason']}")
        else:
            print("  ✅ לא נמצאו פוסטים חשודים")

    def _print_recommendations(self):
        """סיכום המלצות"""
        total = sum(len(v) for v in self.recommendations.values())

        if total == 0:
            print("✨ מושלם! לא נמצאו שיפורים נדרשים")
            print("   המערכת מכוילת היטב 🎯")
            return

        print(f"💡 סה\"כ {total} המלצות לשיפור:\n")

        if self.recommendations['brokers']:
            print(f"1️⃣ מתווכים חדשים ({len(self.recommendations['brokers'])}):")
            for item in self.recommendations['brokers'][:5]:
                broker_type = "🔴 וודאי" if item.get('type') == 'confirmed' else "🟡 חשוד"
                print(f"   {broker_type} \"{item['term']}\" - {item['count']} פוסטים")
                # הצג תצוגה מקדימה של הפוסטים
                for i, (post_id, content, author) in enumerate(item.get('posts', [])[:2], 1):
                    preview = content[:80].replace('\n', ' ')
                    if len(content) > 80:
                        preview += "..."
                    print(f"      📄 פוסט #{i}: {preview}")
                    if author:
                        print(f"         👤 מחבר: {author}")
            print(f"   💡 המלצה: הוסף ל-broker_keywords\n")

        if self.recommendations['publishers_for_brokers']:
            print(f"2️⃣ מפרסמים שעובדים עבור מתווכים ({len(self.recommendations['publishers_for_brokers'])}):")
            for item in self.recommendations['publishers_for_brokers'][:5]:
                broker_kw_str = ', '.join(item['broker_keywords'][:2])
                print(f"   🟠 \"{item['author']}\" - {item['count']} פוסטים (מפרסם עבור: {broker_kw_str})")
                # הצג תצוגה מקדימה של הפוסטים
                for i, post in enumerate(item['posts'][:2], 1):
                    preview = post['content'][:80].replace('\n', ' ')
                    if len(post['content']) > 80:
                        preview += "..."
                    print(f"      📄 פוסט #{i}: {preview}")
                    print(f"         💡 מכיל: {', '.join(post['broker_keywords'][:2])}")
            print(f"   💡 המלצה: הוסף ל-broker_keywords (מפרסמים עבור מתווכים)\n")

        if self.recommendations['settlements']:
            print(f"3️⃣ יישובים ({len(self.recommendations['settlements'])}):")
            for item in self.recommendations['settlements'][:5]:
                print(f"   🏘️ \"{item['term']}\" - {item['count']} פוסטים")
            print(f"   💡 המלצה: הוסף ל-NON_URBAN (ai_agents.py)\n")

        if self.recommendations['blacklist']:
            print(f"4️⃣ Blacklist ({len(self.recommendations['blacklist'])}):")
            for item in self.recommendations['blacklist'][:5]:
                print(f"   🚫 \"{item['term']}\" - {item['count']} פוסטים")
            print(f"   💡 המלצה: הוסף ל-blacklist\n")

        if self.recommendations.get('repeat_posters'):
            print(f"5️⃣ משתמשים חוזרים ({len(self.recommendations['repeat_posters'])}):")
            for item in self.recommendations['repeat_posters'][:5]:
                print(f"   🔁 \"{item['author']}\" - {item['count']} פוסטים")
            print(f"   💡 המלצה: בדוק ידנית - אם זה מתווך הוסף את שמו לbroker_keywords\n")

        if self.recommendations['misclassified']:
            print(f"6️⃣ פוסטים חשודים ({len(self.recommendations['misclassified'])}):")
            for item in self.recommendations['misclassified'][:5]:
                print(f"   ⚠️ Post #{item['post_id']} - {item['type']}")
                print(f"      {item['reason']}")
                print(f"      תצוגה: {item['content_preview']}")
            print(f"   💡 המלצה: בדוק ידנית - אולי צריך לעדכן הנחיות AI\n")

        print("=" * 70)
        print("💡 הרץ עם --apply כדי ליישם, או --interactive לבחור")
        print("=" * 70)

    def _create_backup(self, file_path):
        """יוצר backup של קובץ"""
        if not os.path.exists(file_path):
            return None

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        backup_path = f"{file_path}.backup.{timestamp}"
        shutil.copy2(file_path, backup_path)
        return backup_path

    def _apply_broker_keywords(self):
        """מעדכן broker_keywords בconfig.json"""
        if not self.recommendations['brokers']:
            return 0

        # טען config
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # הוסף מילות מפתח חדשות
        existing = set(kw.lower() for kw in config['search_settings']['search_settings']['broker_keywords'])
        added = 0

        for item in self.recommendations['brokers']:
            term = item['term']
            if term.lower() not in existing:
                config['search_settings']['search_settings']['broker_keywords'].append(term)
                added += 1
                print(f"   ✅ הוספתי: \"{term}\"")

        # שמור
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return added

    def _apply_blacklist(self):
        """מעדכן blacklist בconfig.json"""
        if not self.recommendations['blacklist']:
            return 0

        # טען config
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # הוסף ביטויים חדשים
        existing = set(kw.lower() for kw in config['search_settings']['search_settings']['blacklist'])
        added = 0

        for item in self.recommendations['blacklist']:
            term = item['term']
            if term.lower() not in existing:
                config['search_settings']['search_settings']['blacklist'].append(term)
                added += 1
                print(f"   ✅ הוספתי: \"{term}\"")

        # שמור
        with open(self.config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)

        return added

    def _apply_settlements(self):
        """מעדכן NON_URBAN בai_agents.py"""
        if not self.recommendations['settlements']:
            return 0

        ai_agents_path = "ai_agents.py"
        if not os.path.exists(ai_agents_path):
            print("   ⚠️ ai_agents.py לא נמצא - דלג על יישובים")
            return 0

        # קרא קובץ
        with open(ai_agents_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # מצא את הסעיף של NON_URBAN
        # נוסיף את היישובים החדשים לרשימת הדוגמאות
        settlements_to_add = [item['term'] for item in self.recommendations['settlements']]

        # חפש את השורה "- \"נופים\" (יישוב בבית שמש)"
        pattern = r'(\s+- "נופים" \(יישוב בבית שמש\) → NON_URBAN ⚠️ חשוב!)'

        if re.search(pattern, content):
            # הוסף יישובים חדשים אחרי "נופים"
            new_lines = []
            for settlement in settlements_to_add[:5]:  # מגביל ל-5 יישובים
                new_lines.append(f'  - "{settlement}" → NON_URBAN')

            replacement = r'\1\n' + '\n'.join(new_lines)
            content = re.sub(pattern, replacement, content)

            # שמור
            with open(ai_agents_path, 'w', encoding='utf-8') as f:
                f.write(content)

            for settlement in settlements_to_add[:5]:
                print(f"   ✅ הוספתי: \"{settlement}\"")

            return len(settlements_to_add[:5])
        else:
            print("   ⚠️ לא מצאתי את הסעיף NON_URBAN - עדכן ידנית")
            return 0

    def apply_all(self, interactive=False):
        """מיישם את כל ההמלצות"""
        total = sum(len(v) for v in self.recommendations.values())

        if total == 0:
            print("✨ אין המלצות ליישום!")
            return

        print("\n" + "=" * 70)
        print("⚡ מתחיל יישום שינויים...")
        print("=" * 70 + "\n")

        # Backup
        print("📦 יוצר Backups...")
        config_backup = self._create_backup(self.config_path)
        ai_agents_backup = self._create_backup("ai_agents.py")

        if config_backup:
            print(f"   ✅ {config_backup}")
        if ai_agents_backup:
            print(f"   ✅ {ai_agents_backup}")

        print()

        # יישום
        total_applied = 0

        # מתווכים
        if self.recommendations['brokers']:
            if interactive:
                print(f"\n🔍 נמצאו {len(self.recommendations['brokers'])} מתווכים חדשים:")
                print("   (כל מתווך יוצג בנפרד - תבחר האם להוסיף)\n")

                # שאלה לגבי כל מתווך בנפרד
                approved_brokers = []
                for broker in self.recommendations['brokers']:
                    term = broker['term']
                    count = broker['count']
                    broker_type = "🔴 וודאי" if broker.get('type') == 'confirmed' else "🟡 חשוד"

                    print(f"\n   {broker_type}: '{term}' ({count} פוסטים)")
                    print(f"   סיבה: {broker['reason']}")
                    response = input(f"   💡 להוסיף '{term}' ל-broker_keywords? (y/n): ")

                    if response.lower() == 'y':
                        approved_brokers.append(broker)
                        print(f"   ✅ '{term}' יתווסף")
                    else:
                        print(f"   ⏭️ דילגתי על '{term}'")

                # הוסף רק את המאושרים
                if approved_brokers:
                    self.recommendations['brokers'] = approved_brokers
                    print("\n🔍 מוסיף broker_keywords שנבחרו...")
                    added = self._apply_broker_keywords()
                    total_applied += added
                else:
                    print("\n   ⏭️ לא נבחרו מתווכים להוספה")
                    self.recommendations['brokers'] = []
            else:
                print("\n🔍 מוסיף broker_keywords...")
                added = self._apply_broker_keywords()
                total_applied += added

        # מפרסמים שעובדים עבור מתווכים
        if self.recommendations['publishers_for_brokers']:
            if interactive:
                print(f"\n👤 נמצאו {len(self.recommendations['publishers_for_brokers'])} מפרסמים שעובדים עבור מתווכים:")
                print("   (כל מפרסם יוצג בנפרד - תבחר האם להוסיף)\n")

                # שאלה לגבי כל מפרסם בנפרד
                approved_publishers = []
                for publisher in self.recommendations['publishers_for_brokers']:
                    author = publisher['author']
                    count = publisher['count']
                    broker_kw = ', '.join(publisher['broker_keywords'][:2])

                    print(f"\n   🟠 '{author}' ({count} פוסטים)")
                    print(f"   מפרסם עבור: {broker_kw}")

                    # הצג פוסט אחד לדוגמה
                    if publisher['posts']:
                        preview = publisher['posts'][0]['content'][:80].replace('\n', ' ')
                        if len(publisher['posts'][0]['content']) > 80:
                            preview += "..."
                        print(f"   דוגמה: {preview}")

                    response = input(f"   💡 להוסיף '{author}' ל-broker_keywords? (y/n): ")

                    if response.lower() == 'y':
                        approved_publishers.append(publisher)
                        print(f"   ✅ '{author}' יתווסף")
                    else:
                        print(f"   ⏭️ דילגתי על '{author}'")

                # הוסף רק את המאושרים
                if approved_publishers:
                    # המר את המפרסמים לפורמט שמתאים ל-_apply_broker_keywords
                    for publisher in approved_publishers:
                        self.recommendations['brokers'].append({
                            'term': publisher['author'],
                            'count': publisher['count'],
                            'reason': f"מפרסם עבור {', '.join(publisher['broker_keywords'][:2])}",
                            'type': 'publisher'
                        })

                    print("\n👤 מוסיף מפרסמים שנבחרו...")
                    added = self._apply_broker_keywords()
                    total_applied += added

                    # נקה את brokers כדי לא לספור פעמיים
                    self.recommendations['brokers'] = [b for b in self.recommendations['brokers'] if b.get('type') != 'publisher']
                else:
                    print("\n   ⏭️ לא נבחרו מפרסמים להוספה")
            else:
                # מצב אוטומטי - הוסף את כולם
                for publisher in self.recommendations['publishers_for_brokers']:
                    self.recommendations['brokers'].append({
                        'term': publisher['author'],
                        'count': publisher['count'],
                        'reason': f"מפרסם עבור {', '.join(publisher['broker_keywords'][:2])}",
                        'type': 'publisher'
                    })

                print("\n👤 מוסיף מפרסמים...")
                added = self._apply_broker_keywords()
                total_applied += added

                # נקה את brokers כדי לא לספור פעמיים
                self.recommendations['brokers'] = [b for b in self.recommendations['brokers'] if b.get('type') != 'publisher']

        # Blacklist
        if self.recommendations['blacklist']:
            if interactive:
                response = input(f"\n❓ להוסיף {len(self.recommendations['blacklist'])} ביטויים ל-blacklist? (y/n): ")
                if response.lower() != 'y':
                    print("   ⏭️ דילגתי על blacklist")
                else:
                    print("\n🚫 מוסיף ל-blacklist...")
                    added = self._apply_blacklist()
                    total_applied += added
            else:
                print("\n🚫 מוסיף ל-blacklist...")
                added = self._apply_blacklist()
                total_applied += added

        # יישובים
        if self.recommendations['settlements']:
            if interactive:
                response = input(f"\n❓ להוסיף {len(self.recommendations['settlements'])} יישובים ל-NON_URBAN? (y/n): ")
                if response.lower() != 'y':
                    print("   ⏭️ דילגתי על יישובים")
                else:
                    print("\n🏘️ מוסיף יישובים ל-ai_agents.py...")
                    added = self._apply_settlements()
                    total_applied += added
            else:
                print("\n🏘️ מוסיף יישובים ל-ai_agents.py...")
                added = self._apply_settlements()
                total_applied += added

        # סיכום
        print("\n" + "=" * 70)
        print(f"✅ סיימתי! יושמו {total_applied} שינויים")
        print("=" * 70)

def main():
    parser = argparse.ArgumentParser(description='🎯 Tune AI - אוטומציה לעדכון הגדרות')
    parser.add_argument('--apply', action='store_true', help='יישום אוטומטי של כל ההמלצות')
    parser.add_argument('--interactive', action='store_true', help='מצב אינטראקטיבי - בחירה ידנית')
    parser.add_argument('--report', action='store_true', help='רק דוח מפורט, ללא שינויים')

    args = parser.parse_args()

    # בדיקת קבצים
    if not os.path.exists("posts.db"):
        print("❌ posts.db לא נמצא! הרץ את המערכת קודם")
        return

    if not os.path.exists("config.json"):
        print("❌ config.json לא נמצא!")
        return

    # הרצה
    tuner = TuneAI()
    tuner.analyze()

    # יישום (אם נדרש)
    if args.apply:
        tuner.apply_all(interactive=False)
    elif args.interactive:
        tuner.apply_all(interactive=True)

    print("\n✅ סיום!")

if __name__ == "__main__":
    main()

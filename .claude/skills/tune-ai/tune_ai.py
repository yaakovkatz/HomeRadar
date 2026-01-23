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
            'settlements': [],
            'blacklist': [],
            'spam': [],
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

        # 3. זיהוי יישובים
        print("\n" + "-" * 70)
        print("🏘️ מחפש יישובים לא רלוונטיים...")
        self._find_settlements()

        # 4. ביטויים לblacklist
        print("\n" + "-" * 70)
        print("🚫 מחפש ביטויים חדשים לחסימה...")
        self._find_blacklist_terms()

        # 5. זיהוי פוסטים שסווגו לא נכון
        print("\n" + "-" * 70)
        print("⚠️ מחפש פוסטים שאולי סווגו לא נכון...")
        self._find_misclassified_posts()

        # 6. סיכום המלצות
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
        """מוצא שמות מתווכים חדשים"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # שלוף פוסטים שסומנו כמתווכים
            cursor.execute("""
                SELECT content, author, ai_reason
                FROM posts
                WHERE is_broker = 1 OR category = 'BROKER'
                LIMIT 100
            """)

            broker_posts = cursor.fetchall()

        # טען broker_keywords קיימים
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        existing_keywords = set(kw.lower() for kw in config['search_settings']['search_settings']['broker_keywords'])

        # חלץ שמות חברות
        broker_names = []
        patterns = [
            r'נדל["\']ן\s+(\w+)',  # נדל"ן X
            r'(\w+)\s+נכסים',      # X נכסים
            r'Real\s+Estate\s+(\w+)',  # Real Estate X
            r'מתווך[ת]?\s+(\w+)',  # מתווך X
        ]

        for content, author, reason in broker_posts:
            text = content + " " + (author or "") + " " + (reason or "")

            for pattern in patterns:
                matches = re.findall(pattern, text, re.IGNORECASE)
                broker_names.extend(matches)

        # ספור תדירויות
        counter = Counter(broker_names)

        # סנן רק חדשים ופופולריים
        for name, count in counter.most_common(10):
            if count >= 3 and name.lower() not in existing_keywords:
                self.recommendations['brokers'].append({
                    'term': name,
                    'count': count,
                    'reason': f"מופיע {count} פעמים בפוסטי מתווכים"
                })

        # הדפסה
        if self.recommendations['brokers']:
            print(f"  💡 נמצאו {len(self.recommendations['brokers'])} מתווכים חדשים:")
            for item in self.recommendations['brokers'][:5]:
                print(f"     🔍 '{item['term']}' - {item['count']} פוסטים")
        else:
            print("  ✅ לא נמצאו מתווכים חדשים")

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
                found_keywords = [kw for kw in broker_keywords if kw in text]

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
                print(f"   🔍 \"{item['term']}\" - {item['count']} פוסטים")
            print(f"   💡 המלצה: הוסף ל-broker_keywords\n")

        if self.recommendations['settlements']:
            print(f"2️⃣ יישובים ({len(self.recommendations['settlements'])}):")
            for item in self.recommendations['settlements'][:5]:
                print(f"   🏘️ \"{item['term']}\" - {item['count']} פוסטים")
            print(f"   💡 המלצה: הוסף ל-NON_URBAN (ai_agents.py)\n")

        if self.recommendations['blacklist']:
            print(f"3️⃣ Blacklist ({len(self.recommendations['blacklist'])}):")
            for item in self.recommendations['blacklist'][:5]:
                print(f"   🚫 \"{item['term']}\" - {item['count']} פוסטים")
            print(f"   💡 המלצה: הוסף ל-blacklist\n")

        if self.recommendations['misclassified']:
            print(f"4️⃣ פוסטים חשודים ({len(self.recommendations['misclassified'])}):")
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
                response = input(f"\n❓ להוסיף {len(self.recommendations['brokers'])} מתווכים חדשים? (y/n): ")
                if response.lower() != 'y':
                    print("   ⏭️ דילגתי על מתווכים")
                else:
                    print("\n🔍 מוסיף broker_keywords...")
                    added = self._apply_broker_keywords()
                    total_applied += added
            else:
                print("\n🔍 מוסיף broker_keywords...")
                added = self._apply_broker_keywords()
                total_applied += added

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

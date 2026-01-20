"""
database.py - ניהול דאטאבייס SQLite
גרסה סופית ומתוקנת: זיהוי רחובות חכם (ללא סוגריים מיותרים), עוגנים, וללא אימוג'ים בטקסט הרחוב.
"""

import sqlite3
from datetime import datetime
import re
import json
import os
from dotenv import load_dotenv  # ← הוסף כאן!

load_dotenv()  # ← הוסף!

from ai_agents import AIAgents


class PostDatabase:
    def __init__(self, db_path="posts.db"):
        self.db_path = db_path
        self._create_tables()
        self._load_locations()
        self._compile_location_patterns()

        # אתחול AI Agents ← הוסף את זה!
        try:
            self.ai_agents = AIAgents()
        except Exception as e:
            print(f"⚠️ AI Agents לא זמינים: {e}")
            self.ai_agents = None

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
                location TEXT,
                price TEXT,
                rooms TEXT,
                phone TEXT,
                group_name TEXT,
                blacklist_match TEXT,
                is_relevant INTEGER DEFAULT 1,

                -- שדות AI חדשים ← הוסף!
                category TEXT DEFAULT 'RELEVANT',
                is_broker INTEGER DEFAULT 0,
                ai_confidence REAL,
                ai_reason TEXT,
                ai_failed INTEGER DEFAULT 0,

                scanned_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        conn.commit()
        conn.close()

    # =================================================================
    #              טוען רשימות ערים, שכונות ו-landmarks מקובץ JSON
    # =================================================================
    def _load_locations(self):

        try:
            # נתיב לקובץ JSON
            locations_file = os.path.join(os.path.dirname(__file__), 'data', 'locations.json')

            # טעינת הקובץ
            with open(locations_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # שמירה כ-attributes
            self.cities = data['cities']
            self.neighborhoods = data['neighborhoods']
            self.landmarks = data['landmarks']
            self.neighborhood_context = data['context_patterns']['neighborhood_context']

            print(
                f"✅ נטענו {len(self.cities)} ערים, {len(self.neighborhoods)} קבוצות שכונות, {len(self.landmarks)} landmarks")

        except FileNotFoundError:
            print("⚠️ קובץ locations.json לא נמצא! משתמש ברשימות ברירת מחדל")
            # רשימות גיבוי בסיסיות
            self.cities = ['ירושלים', 'תל אביב', 'חיפה']
            self.neighborhoods = {}
            self.landmarks = {}
            self.neighborhood_context = r'(?:רחוב|שכונת|אזור)'

        except Exception as e:
            print(f"❌ שגיאה בטעינת locations.json: {e}")
            self.cities = []
            self.neighborhoods = {}
            self.landmarks = {}
            self.neighborhood_context = r'(?:רחוב|שכונת|אזור)'

    def _compile_location_patterns(self):
        """מקמפל regex patterns לביצועים מקסימליים"""

        if self.cities:
            cities_pattern = '|'.join([re.escape(city) for city in self.cities])
            # הסר \b - לא עובד עם עברית!
            self.cities_regex = re.compile(rf'({cities_pattern})', re.IGNORECASE)
        else:
            self.cities_regex = None

        # 2. Patterns לשכונות (לפי עיר)
        self.neighborhoods_regex = {}
        for city, neighborhoods in self.neighborhoods.items():
            if neighborhoods:
                pattern = '|'.join([re.escape(n) for n in neighborhoods])
                self.neighborhoods_regex[city] = re.compile(rf'\b({pattern})\b', re.IGNORECASE)

        # 3. Pattern ללנדמרקס
        if self.landmarks:
            landmarks_pattern = '|'.join([re.escape(lm) for lm in self.landmarks.keys()])
            self.landmarks_regex = re.compile(rf'\b({landmarks_pattern})\b', re.IGNORECASE)
        else:
            self.landmarks_regex = None

        print(f"✅ קומפלו {len(self.cities)} ערים, {len(self.neighborhoods_regex)} קבוצות שכונות")

    def save_post(self, post_data):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:

            # =========================================
            # בדיקה ראשונית: האם הפוסט כבר קיים?
            # =========================================
            post_url = post_data.get('post_url')
            if post_url:
                cursor.execute('SELECT id FROM posts WHERE post_url = ?', (post_url,))
                if cursor.fetchone():
                    return False  # פוסט כבר קיים - לא ממשיכים!

            content = post_data.get('content', '')
            author = post_data.get('author', '')

            # =========================================
            # Agent 1: סינון (תמיד רץ!) - עם תמונות
            # =========================================
            ai_result = None
            images = post_data.get('images', [])  # ← חדש! תפיסת תמונות

            if self.ai_agents:
                try:
                    # שליחת תמונות ל-AI
                    ai_result = self.ai_agents.classify_post(content, author, images)  # ← חדש!

                    # הצגת תוצאה
                    if images:
                        print(
                            f"  🤖 Agent 1 (עם {len(images)} תמונות): {ai_result['category']} (confidence: {ai_result['confidence']:.2f})")
                    else:
                        print(f"  🤖 Agent 1: {ai_result['category']} (confidence: {ai_result['confidence']:.2f})")

                except Exception as e:
                    print(f"  ❌ Agent 1 failed: {e}")

            # בדיקה: האם לסנן? (אבל נשמור בכל מקרה!)
            is_filtered = (ai_result and ai_result['category'] != 'RELEVANT')

            if is_filtered:
                print(f"  🔴 סונן ({ai_result['category']}): {ai_result['reason']}")
                print(f"  💾 שומר ב-DB (כדי לא לבדוק שוב)")

                # ⚡ דילוג על Agent 2 - אין טעם למלא חסרים לספאם!
                # שמירה מהירה ב-DB עם נתונים בסיסיים
                cursor.execute('''
                    INSERT INTO posts (
                        post_url, post_id, content, author, 
                        group_name, is_relevant,
                        category, is_broker, ai_confidence, ai_reason,
                        scanned_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    post_data.get('post_url'),
                    post_data.get('post_id'),
                    content,
                    author,
                    post_data.get('group_name'),
                    0,  # is_relevant = 0 (סונן!)
                    ai_result['category'],
                    1 if ai_result['is_broker'] else 0,
                    ai_result['confidence'],
                    ai_result['reason'],
                    post_data.get('scanned_at', datetime.now())
                ))

                conn.commit()
                return False  # ← חשוב! מחזירים False כדי שלא יופיע כ"חדש"

            # =========================================
            # ✅ אם הגענו לכאן - זה RELEVANT!
            # ממשיכים עם Regex ו-Agent 2
            # =========================================
            details = self.extract_details(content)

            # =========================================
            # Agent 2: מילוי חסרים (רק ל-RELEVANT!)
            # =========================================
            needs_ai = (
                    not details['price'] or
                    not details['city'] or
                    not details['location'] or
                    not details['rooms']  # ← הוסף את זה!
            )

            if needs_ai and self.ai_agents:
                try:
                    print(f"  🤖 Agent 2: ממלא חסרים...")
                    ai_details = self.ai_agents.extract_missing_details(content, details)

                    # מיזוג: AI ממלא רק מה שחסר
                    if not details['price'] and ai_details.get('price'):
                        details['price'] = ai_details['price']
                        print(f"    ✅ מחיר מ-AI: {details['price']}")

                    if not details['city'] and ai_details.get('city'):
                        details['city'] = ai_details['city']
                        print(f"    ✅ עיר מ-AI: {details['city']}")

                    if not details['location'] and ai_details.get('location'):
                        details['location'] = ai_details['location']
                        print(f"    ✅ מיקום מ-AI: {details['location']}")

                except Exception as e:
                    print(f"  ❌ Agent 2 failed: {e}")

            # =========================================
            # שמירה ב-DB
            # =========================================
            cursor.execute('''
                INSERT INTO posts (
                    post_url, post_id, content, author, 
                    city, location, price, rooms, phone,
                    group_name, blacklist_match, is_relevant,
                    category, is_broker, ai_confidence, ai_reason,
                    scanned_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                post_data.get('post_url'),
                post_data.get('post_id'),
                content,
                author,
                details['city'],
                details['location'],  # ← הוסף את זה!
                details['price'],
                details['rooms'],
                details['phone'],
                post_data.get('group_name'),
                post_data.get('blacklist_match'),
                0 if is_filtered else post_data.get('is_relevant', 1),

                # שדות AI
                ai_result['category'] if ai_result else 'RELEVANT',
                1 if (ai_result and ai_result['is_broker']) else 0,
                ai_result['confidence'] if ai_result else None,
                ai_result['reason'] if ai_result else None,

                post_data.get('scanned_at', datetime.now())
            ))

            conn.commit()
            return True


        except Exception as e:

            print(f"⚠️ שגיאה בשמירת פוסט: {str(e)}")
            return False
        finally:
            conn.close()

    # =================================================================
    #              שליפת מזהה הפוסט האחרון (למניעת כפילויות)
    # =================================================================
    def get_last_post_id(self, group_name=None):
        """
        בודק מהו הפוסט האחרון שנשמר בדאטאבייס.
        משמש כדי שנדע מאיזה פוסט להתחיל לסרוק ולא נסרוק פוסטים ישנים שוב.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            if group_name:
                # אם ביקשו קבוצה ספציפית - תביא את הכי חדש מאותה קבוצה
                cursor.execute('SELECT post_id FROM posts WHERE group_name = ? ORDER BY scanned_at DESC LIMIT 1', (group_name,))
            else:
                # אחרת - תביא את הכי חדש בכללי
                cursor.execute('SELECT post_id FROM posts ORDER BY scanned_at DESC LIMIT 1')

            result = cursor.fetchone()

            # אם נמצאה תוצאה תחזיר את ה-ID, אחרת תחזיר None
            return result[0] if result else None

        finally:
            conn.close()

    # =========================================================
    #  שליפת כל הפוסטים (עבור התצוגה בטבלה)
    #  relevant_only: האם להביא רק פוסטים שסומנו כרלוונטיים
    # =========================================================
    def get_all_posts(self, relevant_only=True, limit=100):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # בניית השאילתה חלק-אחרי-חלק
        sql = 'SELECT * FROM posts '
        if relevant_only:
            sql += 'WHERE is_relevant = 1 '
        sql += 'ORDER BY scanned_at DESC LIMIT ?'

        cursor.execute(sql, (limit,))

        # שליפת שמות העמודות (כדי שיהיו לנו "תוויות")
        columns = [description[0] for description in cursor.description]
        rows = cursor.fetchall()

        conn.close()

        # המרת התוצאות למילון (כדי שנוכל לגשת לנתונים לפי שם העמודה)
        return [dict(zip(columns, row)) for row in rows]

    def get_stats(self):
        # =========================================================
        #  הפקת דוח סטטיסטיקות (כמה פוסטים נאספו, כמה רלוונטיים וכו')
        # =========================================================
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # 1. סה"כ פוסטים במערכת
            cursor.execute('SELECT COUNT(*) FROM posts')
            total = cursor.fetchone()[0]

            # 2. כמה מסומנים כרלוונטיים (לא נמחקו/סוננו ידנית)
            cursor.execute('SELECT COUNT(*) FROM posts WHERE is_relevant = 1')
            relevant = cursor.fetchone()[0]

            # 3. כמה סוננו אוטומטית ע"י המילים השחורות
            cursor.execute('SELECT COUNT(*) FROM posts WHERE blacklist_match IS NOT NULL')
            blacklisted = cursor.fetchone()[0]

            # 4. כמה פוסטים חדשים נאספו היום
            cursor.execute("SELECT COUNT(*) FROM posts WHERE DATE(scanned_at) = DATE('now')")
            today = cursor.fetchone()[0]

            # החזרת כל הנתונים כמילון מסודר
            return {
                'total': total,
                'relevant': relevant,
                'blacklisted': blacklisted,
                'today': today
            }

        finally:
            conn.close()

    def get_week_stats(self): return self._get_period_stats(7)
    def get_month_stats(self): return self._get_period_stats(30)

    def _get_period_stats(self, days):
        # =========================================================
        #  פונקציית עזר פנימית לחישוב סטטיסטיקה לפי תקופת זמן
        #  מקבלת מספר ימים (days) ומחזירה כמה רלוונטיים וכמה נחסמו
        # =========================================================
        # וידוא שdays הוא מספר שלם (הגנה מפני SQL injection)
        days = int(days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # בניית מחרוזת התאריך בצורה בטוחה
            date_modifier = f'-{days} days'

            # 1. ספירת רלוונטיים בתקופה
            cursor.execute(
                "SELECT COUNT(*) FROM posts WHERE DATE(scanned_at) >= DATE('now', ?) AND is_relevant = 1",
                (date_modifier,))
            relevant = cursor.fetchone()[0]

            # 2. ספירת חסומים בתקופה
            cursor.execute(
                "SELECT COUNT(*) FROM posts WHERE DATE(scanned_at) >= DATE('now', ?) AND blacklist_match IS NOT NULL",
                (date_modifier,))
            blacklisted = cursor.fetchone()[0]

            return {'relevant': relevant, 'blacklisted': blacklisted}

        finally:
            conn.close()


    #=========================================================
    #מחיקת פוסטים ישנים מהדאטאבייס (תחזוקה וניקוי)
    #=========================================================
    def clear_old_posts(self, days=30):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        try:
            # המטרה: למחוק כל מה שהתאריך שלו 'קטן' (ישן) מהיום פחות X ימים.
            cursor.execute("DELETE FROM posts WHERE scanned_at < datetime('now', '-' || ? || ' days')", (days,))

            # rowcount מחזיר את כמות השורות שהושפעו מהפקודה האחרונה.
            deleted = cursor.rowcount
            conn.commit()
            return deleted
        finally:
            conn.close()

    # =========================================================
    #  ייצוא הנתונים לאקסל (CSV) לשיתוף חיצוני
    # =========================================================
    def export_to_csv(self, filename="apartments_export.csv", relevant_only=True):

        try:
            import pandas as pd  # טוענים את ספריית הנתונים רק כשצריך אותה

            # 1. שליפת הנתונים
            posts = self.get_all_posts(relevant_only=relevant_only, limit=10000)
            if not posts:
                return False

            # 2. המרה לטבלה של פנדס
            df = pd.DataFrame(posts)

            # 3. סידור עמודות (כדי שהחשובות יהיו בהתחלה)
            columns_order = ['id', 'content', 'post_url', 'author', 'group_name', 'blacklist_match', 'scanned_at']
            # הטריק הזה (List Comprehension) מוודא שאנחנו לא מבקשים עמודה שלא קיימת וגורמים לקריסה
            existing_cols = [c for c in columns_order if c in df.columns]
            df = df[existing_cols]

            # 4. שמירה לקובץ
            # index=False: לא שומר את המספרים הסידוריים של פנדס (0,1,2...) בצד
            df.to_csv(filename, index=False, encoding='utf-8-sig')
            return True

        except Exception as e:
            # זה קורה בדרך כלל אם הקובץ פתוח כבר באקסל והמחשב לא נותן לשמור עליו
            print(f"שגיאה בייצוא לקובץ: {e}")
            return False

    # =================================================================
    #              יצירת תצוגה מקוצרת ("כותרת") עבור הטבלה בממשק
    # =================================================================

    def extract_summary(self, content):

        if not content:
            return ""

        # 1. שימוש במנוע ה-Regex כדי לחלץ את הפרטים החשובים
        details = self.extract_details(content)

        parts = []
        if details['city']: parts.append(details['city'])
        if details['price']: parts.append(f"{details['price']} ₪")
        if details['rooms']: parts.append(f"{details['rooms']} חד'")

        # מחבר את החלקים עם קו מפריד יפה
        summary = " | ".join(parts)

        # 2. מנגנון 'תוכנית גיבוי' (Fallback):
        # אם ה-Regex לא הצליח לחלץ כלום (התקציר ריק או קצר מדי),
        # ניקח את ה-50 תווים הראשונים של הפוסט המקורי כדי שלא תהיה שורה ריקה.
        if len(summary) < 5:
            # מנקה ירידות שורה (\n) כדי שהכל יהיה בשורה אחת ישרה
            return content.replace('\n', ' ').strip()[:50] + "..."

        return summary

    # =================================================================
    # מחלץ פרטים - גרסה משודרגת
    # =================================================================
    def extract_details(self, content):
        """
        מחלץ פרטים - גרסה משופרת עם זיהוי עיר לפני רחוב
        """
        #print(f"🔍 DEBUG Content: {repr(content[:300])}")

        if not content:
            return {'city': None, 'location': None, 'price': None, 'rooms': None, 'phone': None}

        details = {'city': None, 'location': None, 'price': None, 'rooms': None, 'phone': None}
        content_clean = content.replace('\n', ' ')


        # 1. זיהוי מחיר

        # תבנית 1: מספר (עם או בלי פסיקים) + סימן מטבע
        price_patterns = [
            # עם פסיקים/נקודות
            r'(\d{1,3}(?:[,\.]\d{3})+)(?:\s+\w+){0,5}?\s*(?:₪|ש"ח|שח|שקלים)',
            # בלי פסיקים (4-8 ספרות)
            r'(\d{4,8})\s*(?:₪|ש"ח|שח|שקלים)'
        ]

        price_match = None
        for pattern in price_patterns:
            price_match = re.search(pattern, content)
            if price_match:
                break

        # תבנית 2: "מחיר" + מספר (עם או בלי פסיקים)
        if not price_match:
            price_patterns_2 = [
                # עם פסיקים
                r'(?:מחיר|במחיר|מבוקש|ביקוש)(?:\s+\w+){0,3}?\s*[:\-]?\s*(\d{1,3}(?:[,\.]\d{3})+)',
                # בלי פסיקים
                r'(?:מחיר|במחיר|מבוקש|ביקוש)(?:\s+\w+){0,3}?\s*[:\-]?\s*(\d{4,8})'
            ]

            for pattern in price_patterns_2:
                price_match = re.search(pattern, content)
                if price_match:
                    break

        # תבנית 3: מספר גדול סתם (גיבוי) - רק עם פסיקים
        if not price_match:
            all_numbers = re.findall(r'(\d{1,3}(?:[,\.]\d{3})+)', content)
            for num_str in all_numbers:
                try:
                    clean_num = int(num_str.replace(',', '').replace('.', ''))
                    if 500000 <= clean_num <= 50000000:
                        details['price'] = str(clean_num)
                        break
                except (ValueError, TypeError):
                    pass

        # עיבוד התוצאה
        if price_match and not details['price']:
            try:
                clean_price = price_match.group(1).replace(',', '').replace('.', '')
                price_int = int(clean_price)
                # בדיקת טווח סביר
                if 1000 <= price_int <= 50000000:
                    details['price'] = clean_price
            except (ValueError, TypeError):
                pass

        # =========================================================
        # 2. זיהוי מיקום - לוגיקה חדשה!
        # =========================================================

        # 2.1 - עיר מפורשת
        if self.cities_regex:
            # חיפוש עם "ב" + רווח אופציונלי + עיר + (רווח/פסיק/סוף)
            match = re.search(rf'ב\s*({self.cities_regex.pattern})(?:\s|,|\.|\)|$)',
                              content, re.IGNORECASE)
            if match:
                details['city'] = match.group(1)

            # חיפוש עם הקשר אחרי (אם עדיין לא מצאנו)
            if not details['city']:
                match = re.search(rf'({self.cities_regex.pattern})\s+(?:רחוב|דירה|למכירה|להשכרה)',
                                  content, re.IGNORECASE)
                if match:
                    details['city'] = match.group(1)

        # 2.2 - אם מצאנו עיר, חפש שכונה/רחוב (מהיר!)
        if details['city']:
            # חיפוש שכונה - רק עם הקשר מפורש!
            # זה מונע זיהוי שגוי כמו "קניון הדר תלפיות" → "תלפיות"
            if details['city'] in self.neighborhoods:
                for neighborhood in self.neighborhoods[details['city']]:
                    # חיפוש רק עם הקשר: "בשכונת X", "שכונת X", וכו'
                    pattern = r'(?:בשכונת|שכונת|באזור|אזור)\s+' + re.escape(neighborhood)
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        details['location'] = neighborhood
                        break

            # אם לא מצאנו שכונה, חפש רחוב
            if not details['location']:
                street_pattern = r"(?:רחוב|רח'|רח|שדרות|סמטת|דרך)\s+([א-ת\s\"']+?)(?=\s*\)|\s*\d|\s*,|\s*\.|\s*$)"
                match = re.search(street_pattern, content_clean)
                if match:
                    street = match.group(1).strip()
                    if 2 < len(street) < 25:
                        details['location'] = f"רחוב {street}"

        # 2.3 - אם אין עיר, חפש שכונה ידועה
        if not details['city']:
            for city, neighborhoods in self.neighborhoods.items():
                for neighborhood in neighborhoods:
                    # חיפוש עם הקשר
                    pattern = r'(?:ב|שכונת|אזור)\s+' + re.escape(neighborhood)
                    if re.search(pattern, content):
                        details['city'] = city
                        details['location'] = neighborhood
                        break
                if details['city']:
                    break

        # 2.4 - אם אין עיר, חפש landmark (מהיר!)
        if not details['city'] and self.landmarks_regex:
            match = re.search(rf'(?:ב|ליד|קרוב ל|סמוך ל)\s+({self.landmarks_regex.pattern})',
                              content, re.IGNORECASE)
            if match:
                landmark = match.group(1)
                details['city'] = self.landmarks.get(landmark)
                details['location'] = f"ליד {landmark}"

        # 2.5 - אם אין עיר, חפש ערים עם הקשר (מהיר!)
        if not details['city'] and self.cities_regex:
            # חיפוש עם הקשרים שונים
            context_patterns = [
                rf'ב({self.cities_regex.pattern})',
                rf'[,\.]\s*({self.cities_regex.pattern})',
                rf'({self.cities_regex.pattern})\s+(?:רחוב|דירה|למכירה)',
                rf'(?:עיר|בעיר)\s+({self.cities_regex.pattern})'
            ]

            for pattern in context_patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    city = match.group(1)
                    details['city'] = city.replace('-', ' ').replace('"', '')
                    break


        # 3. טלפון (כולל פורמט בינלאומי)

        phone_patterns = [
            # פורמט בינלאומי: +972-XX-XXX-XXXX
            r'\+972[\s\-]?5\d[\s\-]?\d{3}[\s\-]?\d{4}',
            r'\+972[\s\-]?5\d[\s\-]?\d{7}',

            # פורמט ישראלי רגיל (הקוד הישן שלך)
            r'0\d{1,2}[-\s\.]?\d{3}[-\s\.]?\d{4}',
            r'\(0\d{1,2}\)\s?\d{3}[-\s]?\d{4}',
            r'0\d{1,2}[-\s]?\d{3}[-\s]?\d{2}[-\s]?\d{2}'
        ]

        for pattern in phone_patterns:
            phone_match = re.search(pattern, content)
            if phone_match:
                raw_phone = phone_match.group(0)

                # ניקוי: הסר +972 והחלף ב-0
                if raw_phone.startswith('+972'):
                    raw_phone = '0' + raw_phone[4:]  # הסר +972 והוסף 0

                # הסר כל מה שלא ספרה
                details['phone'] = re.sub(r'[^\d]', '', raw_phone)
                break

        # 4. חדרים - תומך ב: "2 חדרים", "2.5 חד'", "2 וחצי חדרים"
        rooms_patterns = [
            r'(\d+(?:\.\d+)?)\s*(?:וחצי\s+)?(?:חדרים|חדר|חד\'|חד)',  # 2 וחצי חדרים
            r'(\d+\.5)\s*(?:חדרים|חדר|חד\'|חד)',  # 2.5 חדרים
        ]

        rooms_match = None
        for pattern in rooms_patterns:
            rooms_match = re.search(pattern, content)
            if rooms_match:
                break

        if rooms_match:
            details['rooms'] = rooms_match.group(1)

        return details  # ← הוסף את זה!


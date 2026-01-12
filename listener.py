"""
listener.py - מאזין רציף לפוסטים חדשים בפייסבוק
גרסה מעודכנת: שימוש ב-SettingsManager
"""

import time
import random
from datetime import datetime, time as dt_time
import threading
from scraper import FacebookScraper
from database import PostDatabase
import json
import os
from settings_manager import SettingsManager


class FacebookListener:
    """מאזין רציף לפוסטים חדשים"""

    def __init__(self, config_path="config.json"):
        """אתחול המאזין"""
        # ישן - נשאר לביטחון (נמחק בשלב 4)
        self.config = self._load_config(config_path)

        # חדש - זה מה שנשתמש בו
        self.settings = SettingsManager(config_path)

        self.db = PostDatabase()
        self.scraper = None
        self.is_listening = False
        self.is_cleaning = False
        self.stats = {
            'checks_today': 0,
            'new_posts': 0,
            'blacklisted': 0,
            'last_check': None,
            'next_check': None
        }
        self.status_callback = None
        self.settings.on_change(self._on_settings_changed)

    def _load_config(self, config_path):
        """טוען הגדרות - ישן, נשאר לביטחון"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise Exception("קובץ config.json לא נמצא!")

    def set_status_callback(self, callback):
        """מגדיר פונקציה לעדכון סטטוס בממשק"""
        self.status_callback = callback

    def _log(self, message):
        """מדפיס הודעה"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        print(full_message)

        if self.status_callback:
            self.status_callback(full_message)

    def _on_settings_changed(self, key, value):
        """
        נקרא אוטומטית כשהגדרה משתנתה

        Args:
            key: המפתח שהשתנה (למשל: 'listener.check_interval_min')
            value: הערך החדש
        """
        self._log(f"🔄 הגדרה עודכנה: {key} = {value}")

        # טיפול ספציפי לפי סוג ההגדרה
        if key.startswith('listener.'):
            self._log("✅ הגדרות ההאזנה עודכנו - ייכנסו לתוקף בבדיקה הבאה")

        elif key.startswith('search_settings.blacklist'):
            self._log("✅ Blacklist עודכן - ייכנס לתוקף בבדיקה הבאה")

        elif key == 'groups_urls':
            self._log("✅ רשימת קבוצות עודכנה - ייכנס לתוקף בבדיקה הבאה")

        # אפשר להוסיף לוגיקה נוספת כאן...
        # למשל: עדכון מיידי של משתנים

    def _is_active_hours(self):
        """בודק אם אנחנו בשעות פעילות"""
        now = datetime.now().time()

        # חדש - משתמשים ב-settings
        start_hour = self.settings.get('listener.active_hours_start', 8)
        end_hour = self.settings.get('listener.active_hours_end', 23)

        # ישן - מוערת
        # start_hour = self.config['listener']['active_hours_start']
        # end_hour = self.config['listener']['active_hours_end']

        start_time = dt_time(start_hour, 0)
        end_time = dt_time(end_hour, 0)

        return start_time <= now <= end_time

    def _check_blacklist(self, content):
        """
        בודק אם הפוסט מכיל מילה מה-blacklist (עם תמיכה ב-whitelist)

        Returns:
            None אם תקין, או את המילה שנתפסה
        """
        content_lower = content.lower()

        # שלב 1: בדוק whitelist - אם יש התאמה, אל תסנן!
        whitelist = self.settings.get('search_settings.whitelist', [])
        for phrase in whitelist:
            if phrase.lower() in content_lower:
                # נמצאה ביטוי מה-whitelist - זה פוסט לגיטימי!
                return None

        # שלב 2: רק עכשיו בדוק blacklist
        blacklist = self.settings.get('search_settings.blacklist', [])
        for word in blacklist:
            if word.lower() in content_lower:
                return word  # נמצאה מילה אסורה

        return None

    def _process_posts(self, posts, group_name):
        """
        מעבד רשימת פוסטים - בודק blacklist ושומר ב-DB
        """
        last_known_id = self.db.get_last_post_id(group_name)

        new_count = 0
        blacklisted_count = 0

        for post in posts:
            if post['post_id'] == last_known_id:
                break

            blacklist_match = self._check_blacklist(post['content'])

            post_data = {
                'post_url': post['post_url'],
                'post_id': post['post_id'],
                'content': post['content'],
                'author': post['author'],
                'group_name': group_name,
                'blacklist_match': blacklist_match,
                'is_relevant': 1 if blacklist_match is None else 0,
                'scanned_at': datetime.now()
            }

            saved = self.db.save_post(post_data)

            if saved:
                new_count += 1
                if blacklist_match:
                    blacklisted_count += 1
                    self._log(f"  🔴 סונן: '{post['content'][:50]}...' (מילה: {blacklist_match})")
                else:
                    self._log(f"  🟢 חדש: '{post['content'][:50]}...'")

        return new_count, blacklisted_count

    def _ensure_browser_ready(self):
        """מוודא שהדפדפן פתוח ופעיל"""
        if not self.scraper:
            self._log("⚠️ אין scraper - יוצר חדש...")
            try:
                self.scraper = FacebookScraper()
                self.scraper.create_driver()
                self._log("✓ דפדפן נוצר בהצלחה")
                return True
            except Exception as e:
                self._log(f"❌ נכשל ליצור דפדפן: {str(e)}")
                return False

        if not self.scraper.driver:
            self._log("⚠️ אין driver - יוצר חדש...")
            try:
                self.scraper.create_driver()
                self._log("✓ driver נוצר בהצלחה")
                return True
            except Exception as e:
                self._log(f"❌ נכשל ליצור driver: {str(e)}")
                return False

        try:
            _ = self.scraper.driver.current_url
            return True
        except:
            self._log("⚠️ דפדפן לא מגיב - פותח מחדש...")
            try:
                self.scraper.close()
                self.scraper = FacebookScraper()
                self.scraper.create_driver()
                self._log("✓ דפדפן נפתח מחדש בהצלחה")
                return True
            except Exception as e:
                self._log(f"❌ נכשל לפתוח דפדפן מחדש: {str(e)}")
                self.scraper = None
                return False

    def _single_check(self):
        """מבצע בדיקה בודדת - סורק את כל הקבוצות"""

        self.settings.reload()  # ← הוסף שורה זו!

        # טעינת רשימת קבוצות
        groups_urls = self.settings.get('groups_urls', [])
        groups_names = self.settings.get('groups_names', [])
        posts_to_read = self.settings.get('listener.posts_to_read', 3)

        if not groups_urls:
            self._log("❌ לא הוגדרו קבוצות ב-config!")
            return

        # ודא שיש מספר שווה של שמות
        if len(groups_names) < len(groups_urls):
            # השלם שמות חסרים
            for i in range(len(groups_names), len(groups_urls)):
                groups_names.append(f"קבוצה {i + 1}")

        if not self._ensure_browser_ready():
            self._log("❌ אין דפדפן פעיל - מדלג על בדיקה זו")
            return

        # ========================================
        # לולאה על כל הקבוצות! ← חדש!
        # ========================================
        total_new = 0
        total_filtered = 0

        for idx, group_url in enumerate(groups_urls):
            group_name = groups_names[idx]

            self._log(f"🔍 סורק קבוצה: {group_name}")

            try:
                # סריקת הקבוצה
                posts = self.scraper.quick_read_posts(group_url, max_posts=posts_to_read)

                if not posts:
                    self._log(f"⚠️ לא נמצאו פוסטים בקבוצה '{group_name}'")
                    continue

                self._log(f"📊 נמצאו {len(posts)} פוסטים בקבוצה '{group_name}'")

                # עיבוד פוסטים
                new_count, blacklisted_count = self._process_posts(posts, group_name)

                # צבירת סטטיסטיקות
                total_new += new_count
                total_filtered += blacklisted_count

                self._log(f"✅ קבוצה '{group_name}': {new_count} חדשים ({blacklisted_count} סוננו)")

            except Exception as e:
                self._log(f"❌ שגיאה בסריקת '{group_name}': {str(e)}")
                continue

        # עדכון סטטיסטיקות כלליות
        self.stats['new_posts'] += total_new
        self.stats['blacklisted'] += total_filtered
        self.stats['checks_today'] += 1
        self.stats['last_check'] = datetime.now()

        self._log(f"🎯 סיום מחזור: {total_new} פוסטים חדשים סה״כ ({total_filtered} סוננו)")

        # טיפול בשגיאות דפדפן
        if not self.scraper or not self.scraper.driver:
            try:
                if self.scraper:
                    self.scraper.close()
                self.scraper = None
                self._log("🔄 דפדפן אופס - יפתח מחדש בבדיקה הבאה")
            except:
                pass

    def start_listening(self):
        """מתחיל האזנה רציפה"""
        if self.is_listening:
            self._log("⚠️ כבר מאזין!")
            return False

        if self.is_cleaning:
            self._log("⚠️ מנקה משאבים - חכה קצת...")
            return False

        if self.scraper and self.scraper.driver:
            self._log("🧹 מוצא דפדפן ישן - סוגר...")
            try:
                self.scraper.close()
            except:
                pass
            self.scraper = None

        self.is_listening = True
        self.stats = {
            'checks_today': 0,
            'new_posts': 0,
            'blacklisted': 0,
            'last_check': None,
            'next_check': None
        }

        self._log("🚀 פותח דפדפן חדש...")
        try:
            self.scraper = FacebookScraper()
            self.scraper.create_driver()
            self._log("✓ דפדפן נפתח בהצלחה")
        except Exception as e:
            self._log(f"❌ שגיאה בפתיחת דפדפן: {str(e)}")
            self.is_listening = False
            return False

        thread = threading.Thread(target=self._listen_loop, daemon=True)
        thread.start()

        self._log("🎧 התחלתי להאזין!")
        return True

    def _listen_loop(self):
        """הלולאה הראשית של ההאזנה"""
        try:
            while self.is_listening:
                if not self._is_active_hours():
                    # חדש - משתמשים ב-settings
                    start_hour = self.settings.get('listener.active_hours_start', 8)

                    # ישן - מוערת
                    # start_hour = self.config['listener']['active_hours_start']

                    self._log(f"😴 מחוץ לשעות פעילות - ישן עד {start_hour}:00")
                    time.sleep(3600)
                    continue

                self._single_check()

                # חדש - משתמשים ב-settings
                min_interval = self.settings.get('listener.check_interval_min', 360)
                max_interval = self.settings.get('listener.check_interval_max', 480)

                # ישן - מוערת
                # min_interval = self.config['listener']['check_interval_min']
                # max_interval = self.config['listener']['check_interval_max']

                wait_time = random.randint(min_interval, max_interval)
                self.stats['next_check'] = datetime.now().timestamp() + wait_time

                minutes = wait_time // 60
                self._log(f"⏰ ממתין {minutes} דקות עד הבדיקה הבאה...")

                for _ in range(wait_time // 10):
                    if not self.is_listening:
                        break
                    time.sleep(10)

        except Exception as e:
            self._log(f"❌ שגיאה קריטית בלולאה: {str(e)}")

        finally:
            self._log("🛑 עצרתי להאזין")
            self._cleanup()

    def _cleanup(self):
        """ניקוי משאבים"""
        self.is_cleaning = True

        if self.scraper:
            try:
                self._log("🔒 סוגר דפדפן...")
                self.scraper.close()
                self._log("✓ דפדפן נסגר בהצלחה")
            except Exception as e:
                self._log(f"⚠️ שגיאה בסגירת דפדפן: {str(e)}")
            finally:
                self.scraper = None

        time.sleep(1)
        self.is_cleaning = False
        self._log("✓ ניקוי הושלם")

    def stop_listening(self):
        """עוצר את ההאזנה"""
        if not self.is_listening:
            self._log("⚠️ לא מאזין כרגע")
            return

        self._log("⏸️ עוצר האזנה...")
        self.is_listening = False

        wait_count = 0
        while self.is_cleaning and wait_count < 10:
            time.sleep(1)
            wait_count += 1

        if self.is_cleaning:
            self._log("⚠️ ניקוי עדיין בתהליך - אבל ממשיך")

    def force_cleanup(self):
        """ניקוי כפוי"""
        self._log("🧹 ניקוי כפוי...")
        self.is_listening = False
        time.sleep(2)
        self._cleanup()

    def get_stats(self):
        """מחזיר סטטיסטיקות נוכחיות"""
        db_stats = self.db.get_stats()

        return {
            **self.stats,
            'total_in_db': db_stats['total'],
            'relevant_in_db': db_stats['relevant'],
            'today_in_db': db_stats['today']
        }
"""
listener.py - מאזין רציף לפוסטים חדשים בפייסבוק
"""

import time
import random
from datetime import datetime, time as dt_time
import threading
from scraper import FacebookScraper
from database import PostDatabase
import json
import os


class FacebookListener:
    """מאזין רציף לפוסטים חדשים"""

    def __init__(self, config_path="config.json"):
        """אתחול המאזין"""
        self.config = self._load_config(config_path)
        self.db = PostDatabase()
        self.scraper = None
        self.is_listening = False
        self.is_cleaning = False  # ← חדש! דגל ניקוי
        self.stats = {
            'checks_today': 0,
            'new_posts': 0,
            'blacklisted': 0,
            'last_check': None,
            'next_check': None
        }
        self.status_callback = None

    def _load_config(self, config_path):
        """טוען הגדרות"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            raise Exception("קובץ config.json לא נמצא!")

    def set_status_callback(self, callback):
        """מגדיר פונקציה לעדכון סטטוס בממשק"""
        self.status_callback = callback

    def _log(self, message):
        """מדפיס הודעה (ובעתיד - לקובץ log)"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        full_message = f"[{timestamp}] {message}"
        print(full_message)

        if self.status_callback:
            self.status_callback(full_message)

    def _is_active_hours(self):
        """בודק אם אנחנו בשעות פעילות"""
        now = datetime.now().time()
        start_hour = self.config['listener']['active_hours_start']
        end_hour = self.config['listener']['active_hours_end']

        start_time = dt_time(start_hour, 0)
        end_time = dt_time(end_hour, 0)

        return start_time <= now <= end_time

    def _check_blacklist(self, content):
        """
        בודק אם הפוסט מכיל מילה מה-blacklist

        Returns:
            None אם תקין, או את המילה שנתפסה
        """
        blacklist = self.config.get('blacklist', [])
        content_lower = content.lower()

        for word in blacklist:
            if word.lower() in content_lower:
                return word

        return None

    def _process_posts(self, posts, group_name):
        """
        מעבד רשימת פוסטים - בודק blacklist ושומר ב-DB

        Args:
            posts: רשימת פוסטים
            group_name: שם הקבוצה

        Returns:
            (new_count, blacklisted_count)
        """
        last_known_id = self.db.get_last_post_id(group_name)

        new_count = 0
        blacklisted_count = 0

        # עוברים על הפוסטים מהחדש לישן
        for post in posts:
            # אם הגענו לפוסט שכבר ראינו - עוצרים
            if post['post_id'] == last_known_id:
                break

            # בדיקת blacklist
            blacklist_match = self._check_blacklist(post['content'])

            # הכנת נתונים לשמירה
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

            # שמירה ב-DB
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
        """
        מוודא שהדפדפן פתוח ופעיל - חובה לפני כל בדיקה!

        Returns:
            True אם הדפדפן מוכן, False אחרת
        """
        # בדיקה 1: האם יש scraper?
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

        # בדיקה 2: האם הדרייבר קיים?
        if not self.scraper.driver:
            self._log("⚠️ אין driver - יוצר חדש...")
            try:
                self.scraper.create_driver()
                self._log("✓ driver נוצר בהצלחה")
                return True
            except Exception as e:
                self._log(f"❌ נכשל ליצור driver: {str(e)}")
                return False

        # בדיקה 3: האם הדפדפן חי?
        try:
            _ = self.scraper.driver.current_url
            # אם הגענו לכאן - הדפדפן חי!
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
        """מבצע בדיקה בודדת"""
        group_url = self.config.get('group_url')
        group_name = "קבוצה ראשית"
        posts_to_read = self.config['listener']['posts_to_read']

        self._log("🔍 מתחיל בדיקה...")

        # ===== חובה: וודא שיש דפדפן! =====
        if not self._ensure_browser_ready():
            self._log("❌ אין דפדפן פעיל - מדלג על בדיקה זו")
            return
        # ====================================

        try:
            # קריאת פוסטים
            posts = self.scraper.quick_read_posts(group_url, max_posts=posts_to_read)

            if not posts:
                self._log("⚠️ לא נמצאו פוסטים")
                return

            self._log(f"📊 נמצאו {len(posts)} פוסטים בעמוד")

            # עיבוד
            new_count, blacklisted_count = self._process_posts(posts, group_name)

            # עדכון סטטיסטיקות
            self.stats['new_posts'] += new_count
            self.stats['blacklisted'] += blacklisted_count
            self.stats['checks_today'] += 1
            self.stats['last_check'] = datetime.now()

            self._log(f"✅ הסתיים: {new_count} חדשים ({blacklisted_count} סוננו)")

        except Exception as e:
            self._log(f"❌ שגיאה בבדיקה: {str(e)}")
            # נסה לאתחל דפדפן למקרה הבא
            try:
                if self.scraper:
                    self.scraper.close()
                self.scraper = None
                self._log("🔄 דפדפן אופס - יפתח מחדש בבדיקה הבאה")
            except:
                pass

    def start_listening(self):
        """מתחיל האזנה רציפה (ב-thread)"""
        # בדיקה 1: כבר מאזין?
        if self.is_listening:
            self._log("⚠️ כבר מאזין!")
            return False

        # בדיקה 2: מנקה כרגע?
        if self.is_cleaning:
            self._log("⚠️ מנקה משאבים - חכה קצת...")
            return False

        # בדיקה 3: יש דפדפן ישן?
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

        # פתיחת דפדפן פעם אחת בהתחלה!
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
                # בדיקת שעות פעילות
                if not self._is_active_hours():
                    now = datetime.now().time()
                    start_hour = self.config['listener']['active_hours_start']
                    self._log(f"😴 מחוץ לשעות פעילות (08:00-23:00) - ישן עד {start_hour}:00")

                    # חכה שעה ובדוק שוב
                    time.sleep(3600)
                    continue

                # ביצוע בדיקה
                self._single_check()

                # חישוב זמן המתנה אקראי (6-8 דקות = 360-480 שניות)
                min_interval = self.config['listener']['check_interval_min']
                max_interval = self.config['listener']['check_interval_max']
                wait_time = random.randint(min_interval, max_interval)

                self.stats['next_check'] = datetime.now().timestamp() + wait_time

                minutes = wait_time // 60
                self._log(f"⏰ ממתין {minutes} דקות עד הבדיקה הבאה...")

                # המתנה (עם בדיקה כל 10 שניות אם לעצור)
                for _ in range(wait_time // 10):
                    if not self.is_listening:
                        break
                    time.sleep(10)

        except Exception as e:
            self._log(f"❌ שגיאה קריטית בלולאה: {str(e)}")

        finally:
            # סיום - סגור דפדפן בכל מקרה!
            self._log("🛑 עצרתי להאזין")
            self._cleanup()

    def _cleanup(self):
        """ניקוי משאבים - סגירת דפדפן וכו'"""
        self.is_cleaning = True  # ← סימון שמנקה

        if self.scraper:
            try:
                self._log("🔒 סוגר דפדפן...")
                self.scraper.close()
                self._log("✓ דפדפן נסגר בהצלחה")
            except Exception as e:
                self._log(f"⚠️ שגיאה בסגירת דפדפן: {str(e)}")
            finally:
                self.scraper = None

        import time
        time.sleep(1)  # המתן שנייה לוודא שהכל נסגר

        self.is_cleaning = False  # ← סיימנו לנקות
        self._log("✓ ניקוי הושלם")

    def stop_listening(self):
        """עוצר את ההאזנה"""
        if not self.is_listening:
            self._log("⚠️ לא מאזין כרגע")
            return

        self._log("⏸️ עוצר האזנה...")
        self.is_listening = False

        # חכה שהניקוי יסתיים (מקסימום 10 שניות)
        import time
        wait_count = 0
        while self.is_cleaning and wait_count < 10:
            time.sleep(1)
            wait_count += 1

        if self.is_cleaning:
            self._log("⚠️ ניקוי עדיין בתהליך - אבל ממשיך")

    def force_cleanup(self):
        """ניקוי כפוי - למקרה של יציאה מהתוכנה"""
        self._log("🧹 ניקוי כפוי...")
        self.is_listening = False

        # חכה רגע שהלולאה תעצור
        import time
        time.sleep(2)

        # נקה בכוח
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
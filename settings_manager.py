"""
settings_manager.py - ניהול הגדרות מרכזי
"""

import json
import os
from datetime import datetime


class SettingsManager:
    """
    מנהל הגדרות מרכזי - Singleton
    מאפשר קריאה ושמירה של הגדרות בצורה מרכזית
    """

    _instance = None  # Singleton - רק instance אחד בכל התוכנה

    def __new__(cls, config_path="config.json"):
        """יוצר instance יחיד (Singleton pattern)"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path="config.json"):
        """אתחול - רק פעם אחת"""
        if self._initialized:
            return

        self.config_path = config_path
        self.config = {}
        self.change_listeners = []  # ← הוסף שורה זו!
        self.load()
        self._initialized = True

    def load(self):
        """טוען הגדרות מקובץ JSON"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                print(f"✅ הגדרות נטענו מ-{self.config_path}")
            else:
                print(f"⚠️ קובץ {self.config_path} לא נמצא - יוצר ברירת מחדל")
                self._create_default_config()
        except Exception as e:
            print(f"❌ שגיאה בטעינת הגדרות: {e}")
            self._create_default_config()

    def _create_default_config(self):
        """יוצר config ברירת מחדל"""
        self.config = {
            "chrome_profile_path": "",
            "groups_urls": [],
            "search_settings": {
                "cities": [],
                "blacklist": []
            },
            "listener": {
                "check_interval_min": 360,
                "check_interval_max": 480,
                "active_hours_start": 8,
                "active_hours_end": 23,
                "posts_to_read": 3
            },
            "scraper": {
                "page_load_wait": 5,
                "max_time_on_facebook": 15
            }
        }
        self.save()

    def save(self):
        """שומר הגדרות לקובץ JSON"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"💾 הגדרות נשמרו ב-{self.config_path}")
            return True
        except Exception as e:
            print(f"❌ שגיאה בשמירת הגדרות: {e}")
            return False

    def get(self, key, default=None):
        """
        מחזיר ערך הגדרה

        Examples:
            get('groups_urls')
            get('listener.check_interval_min')
            get('search_settings.blacklist')
        """
        # תמיכה ב-nested keys: 'listener.check_interval_min'
        keys = key.split('.')
        value = self.config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key, value):
        """
        מגדיר ערך הגדרה

        Examples:
            set('groups_urls', ['https://...'])
            set('listener.check_interval_min', 300)
        """
        keys = key.split('.')

        # Navigate to the nested dict
        current = self.config
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        # Auto-save
        self.save()
        self._notify_listeners(key, value)  # ← שורה חדשה!

        return True

    def get_all(self):
        """מחזיר את כל ההגדרות"""
        return self.config.copy()

    def reload(self):
        """טוען מחדש את ההגדרות מהקובץ"""
        print("🔄 טוען הגדרות מחדש...")
        self.load()
        return True

    def on_change(self, callback):
        """
        נרשם לקבלת עדכונים על שינויים בהגדרות

        Args:
            callback: פונקציה שתקרא כש-setting משתנה
                      החתימה: callback(key, value)

        Example:
            settings.on_change(lambda k, v: print(f"Changed: {k} = {v}"))
        """
        if callback not in self.change_listeners:
            self.change_listeners.append(callback)
            print(f"✅ נרשם listener חדש (סה\"כ: {len(self.change_listeners)})")

    def remove_listener(self, callback):
        """מסיר listener"""
        if callback in self.change_listeners:
            self.change_listeners.remove(callback)
            print(f"➖ הוסר listener (נשארו: {len(self.change_listeners)})")

    def _notify_listeners(self, key, value):
        """
        מודיע לכל ה-listeners על שינוי

        Args:
            key: המפתח שהשתנה
            value: הערך החדש
        """
        for callback in self.change_listeners:
            try:
                callback(key, value)
            except Exception as e:
                print(f"⚠️ שגיאה ב-listener: {e}")

    def validate(self):
        """
        בודק תקינות ההגדרות

        Returns:
            (bool, list) - (תקין?, רשימת שגיאות)
        """
        errors = []

        # בדיקה 1: יש groups_urls?
        if not self.get('groups_urls'):
            errors.append("לא הוגדרו קבוצות (groups_urls)")

        # בדיקה 2: listener settings תקינים?
        check_min = self.get('listener.check_interval_min', 0)
        check_max = self.get('listener.check_interval_max', 0)

        if check_min <= 0 or check_max <= 0:
            errors.append("מרווחי בדיקה לא תקינים")

        if check_min > check_max:
            errors.append("מרווח מינימום גדול ממקסימום")

        # בדיקה 3: שעות פעילות
        start_hour = self.get('listener.active_hours_start', 0)
        end_hour = self.get('listener.active_hours_end', 24)

        if not (0 <= start_hour <= 23) or not (0 <= end_hour <= 23):
            errors.append("שעות פעילות לא תקינות")

        return (len(errors) == 0, errors)

    def add_group(self, url):
        """מוסיף קבוצה לרשימה"""
        groups = self.get('groups_urls', [])
        if url not in groups:
            groups.append(url)
            self.set('groups_urls', groups)
            return True
        return False

    def remove_group(self, url):
        """מסיר קבוצה מהרשימה"""
        groups = self.get('groups_urls', [])
        if url in groups:
            groups.remove(url)
            self.set('groups_urls', groups)
            return True
        return False

    def add_blacklist_word(self, word):
        """מוסיף מילה ל-blacklist"""
        blacklist = self.get('search_settings.blacklist', [])
        if word not in blacklist:
            blacklist.append(word)
            self.set('search_settings.blacklist', blacklist)
            return True
        return False

    def remove_blacklist_word(self, word):
        """מסיר מילה מ-blacklist"""
        blacklist = self.get('search_settings.blacklist', [])
        if word in blacklist:
            blacklist.remove(word)
            self.set('search_settings.blacklist', blacklist)
            return True
        return False

    def __repr__(self):
        return f"<SettingsManager: {self.config_path}>"


# ==========================================
#           פונקציות עזר גלובליות
# ==========================================

def get_settings():
    """מחזיר את ה-instance של SettingsManager (קיצור דרך)"""
    return SettingsManager()


# ==========================================
#              בדיקה מהירה
# ==========================================

if __name__ == "__main__":
    """בדיקה מהירה של Event System"""
    print("🧪 בודק Event System...\n")

    # יצירת instance
    settings = SettingsManager()


    # הגדרת listener
    def on_setting_changed(key, value):
        print(f"🔔 שינוי התקבל! {key} = {value}")


    print("📝 נרשם ל-listener...")
    settings.on_change(on_setting_changed)

    print("\n🔧 משנה הגדרה...")
    settings.set('listener.check_interval_min', 300)

    print("\n🔧 משנה עוד הגדרה...")
    settings.set('listener.posts_to_read', 5)

    print("\n✅ Event System עובד!")
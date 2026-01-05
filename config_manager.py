import json
import os


class ConfigManager:
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self.config = {}
        self.load_config()

    def load_config(self):
        """טוען מחדש את ההגדרות מהקובץ"""
        if not os.path.exists(self.config_path):
            return False

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
            return True
        except Exception as e:
            print(f"Error reading config: {e}")
            return False

    # --- שליפת נתונים ---

    def get_groups(self):
        # מחזיר רשימה. אם בטעות כתבת מחרוזת בודדת, הוא יהפוך לרשימה
        urls = self.config.get("groups_urls", [])
        if isinstance(urls, str):
            return [urls]
        return urls

    def get_cities(self):
        return self.config.get("search_settings", {}).get("cities", [])

    def get_blacklist(self):
        return self.config.get("search_settings", {}).get("blacklist", [])

    def get_chrome_path(self):
        return self.config.get("chrome_profile_path", "")

    def get_listener_settings(self):
        return self.config.get("listener", {
            "check_interval_min": 300,
            "check_interval_max": 600,
            "posts_to_read": 3
        })

    def get_scraper_settings(self):
        return self.config.get("scraper", {"page_load_wait": 5})
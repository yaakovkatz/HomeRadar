"""
scraper.py - סורק פייסבוק ללא גלילה (מצב זהיר)
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
import time
import json
import os


class FacebookScraper:
    """סורק פייסבוק במצב זהיר - קריאה מהירה ללא גלילה"""

    def __init__(self, config_path="config.json"):
        """אתחול הסורק"""
        self.driver = None
        self.config = self._load_config(config_path)


    """=================================================================="""

    """"=================================================================="""
    def _load_config(self, config_path):
        """טוען הגדרות"""
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # ברירת מחדל
            return {
                "chrome_profile_path": "",
                "scraper": {
                    "page_load_wait": 5,
                    "max_time_on_facebook": 15
                }
            }

    """=================================================================="""

    """"=================================================================="""
    def _clean_noise(self, text):
        """
        מנקה רעש מהטקסט (לייקים, תגובות וכו')

        Args:
            text: הטקסט המלא

        Returns:
            טקסט נקי
        """
        # רשימת סימנים שמסמנים התחלת רעש
        noise_markers = [
            "\nלייק",
            "\nתגובה",
            "\nשיתוף",
            "\nכתיבת תגובה",
            "\nLike",
            "\nComment",
            "\nShare",
            "\nWrite a comment",
        ]

        # חתוך בסימן הראשון שנמצא
        for marker in noise_markers:
            if marker in text:
                text = text.split(marker)[0]
                break

        return text.strip()
    """=================================================================="""

    """"=================================================================="""
    def create_driver(self):
        """יוצר דפדפן"""
        try:
            options = uc.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')

            # פרופיל קבוע
            profile_path = self.config.get("chrome_profile_path")
            if not profile_path:
                profile_path = os.path.join(os.getcwd(), "fb_bot_profile")

            options.add_argument(f'--user-data-dir={profile_path}')

            self.driver = uc.Chrome(options=options)
            self.driver.maximize_window()
            return True

        except Exception as e:
            raise Exception(f"שגיאה ביצירת דפדפן: {str(e)}")

    """=================================================================="""

    """"=================================================================="""
    def quick_read_posts(self, group_url, max_posts=3):
        """
        קריאה מהירה של פוסטים - ללא גלילה!

        Args:
            group_url: כתובת הקבוצה
            max_posts: כמה פוסטים לקרוא (ברירת מחדל: 3)

        Returns:
            רשימת פוסטים
        """
        posts_data = []

        try:
            # כניסה לקבוצה
            self.driver.get(group_url)
            time.sleep(self.config.get("scraper", {}).get("page_load_wait", 5))

            # קריאת פוסטים - ללא גלילה!
            posts = self.driver.find_elements(By.CSS_SELECTOR, 'div[role="article"]')

            if not posts:
                return []

            # מעבד רק את הפוסטים הראשונים שבמסך
            for idx, post in enumerate(posts[:max_posts], 1):
                try:
                    # לחיצה על "עוד" - לפני שליפת התוכן
                    try:
                        see_more = post.find_element(By.XPATH, ".//*[contains(text(), 'עוד') or contains(text(), 'See more')]")
                        self.driver.execute_script("arguments[0].click();", see_more)
                        time.sleep(0.5)
                    except:
                        pass  # אין כפתור - זה בסדר
                    # תוכן
                    try:
                        content = post.text.strip()
                        # ניקוי רעש
                        content = self._clean_noise(content)
                    except:
                        content = ""

                    # קישור
                    post_url = "לא נמצא"
                    post_id = None

                    try:
                        link_elements = post.find_elements(By.TAG_NAME, "a")
                        for link in link_elements:
                            href = link.get_attribute("href")
                            if href and ("/posts/" in href or "/permalink/" in href):
                                post_url = href.split("?")[0]
                                # חילוץ ID מה-URL
                                if "/posts/" in post_url:
                                    post_id = post_url.split("/posts/")[-1]
                                elif "/permalink/" in post_url:
                                    post_id = post_url.split("/permalink/")[-1]
                                break
                    except:
                        pass

                    # --- חילוץ שם מפרסם (גרסה חכמה) ---
                    author = "לא ידוע"
                    try:
                        # נסיון 1: חיפוש בכותרות (h2 או h3)
                        titles = post.find_elements(By.TAG_NAME, "h2")
                        if not titles:
                            titles = post.find_elements(By.TAG_NAME, "h3")

                        if titles:
                            raw_text = titles[0].text.strip()
                            author = raw_text.split('\n')[0]

                        # נסיון 2: גיבוי (strong)
                        if author == "לא ידוע":
                            strongs = post.find_elements(By.TAG_NAME, "strong")
                            if strongs:
                                author = strongs[0].text.strip()
                    except:
                        pass

                    # שמירה
                    if content and len(content) > 10:
                        posts_data.append({
                            'post_url': post_url,
                            'post_id': post_id,
                            'content': content,
                            'author': author
                        })

                    time.sleep(0.2)  # המתנה קטנה בין פוסטים

                except Exception as e:
                    continue

            return posts_data

        except Exception as e:
            raise Exception(f"שגיאה בקריאת פוסטים: {str(e)}")

    def close(self):
        """סוגר דפדפן"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
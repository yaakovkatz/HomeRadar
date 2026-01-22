#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HomeRadar System Validation Script
בודק שכל רכיבי המערכת טעונים ועובדים כראוי
"""

import os
import json
import sqlite3
from pathlib import Path

def main():
    print("🔍 בדיקת מערכת HomeRadar\n")

    base_dir = Path(__file__).parent
    all_good = True

    # 1. בדיקת מאגר רחובות
    print("📊 מאגר רחובות ממשלתי:")
    streets_path = base_dir / "streets.csv"
    if streets_path.exists():
        with open(streets_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        # ספירת ערים ייחודיות
        cities = set()
        for line in lines:
            parts = line.strip().split(',')
            if len(parts) >= 7:
                city = parts[4].strip()
                if city:
                    cities.add(city)

        print(f"  ✅ streets.csv נטען בהצלחה")
        print(f"  📈 {len(lines):,} רחובות")
        print(f"  🏙️ {len(cities)} ערים")

        # הצגת דוגמאות
        sample_cities = sorted(list(cities))[:5]
        print(f"  📍 דוגמאות: {', '.join(sample_cities)}...")
    else:
        print(f"  ❌ streets.csv לא נמצא בנתיב: {streets_path}")
        all_good = False

    print()

    # 2. בדיקת הגדרות
    print("⚙️ הגדרות מערכת:")
    config_path = base_dir / "config.json"
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)

        # בדיקת broker keywords (נתיב מקונן!)
        try:
            broker_keywords = config['search_settings']['search_settings']['broker_keywords']
            print(f"  ✅ broker_keywords נטען")
            print(f"  📋 {len(broker_keywords)} מילות מפתח")
            if broker_keywords:
                print(f"  🔑 דוגמאות: {', '.join(broker_keywords[:3])}...")
        except KeyError:
            print(f"  ❌ broker_keywords לא נמצא בנתיב: search_settings.search_settings.broker_keywords")
            all_good = False

        # בדיקת whitelist
        try:
            whitelist = config['search_settings']['search_settings']['whitelist']
            print(f"  ✅ whitelist: {len(whitelist)} מונחים")
        except KeyError:
            print(f"  ⚠️ whitelist לא מוגדר")

        # בדיקת blacklist
        try:
            blacklist = config['search_settings']['search_settings']['blacklist']
            print(f"  ✅ blacklist: {len(blacklist)} מונחים")
        except KeyError:
            print(f"  ⚠️ blacklist לא מוגדר")

        print()

        # הצגת פילטרים פעילים
        print("🎯 פילטרים פעילים:")
        cities_filter = config['search_settings']['search_settings'].get('cities', {})
        active_cities = [city for city, enabled in cities_filter.items() if enabled]
        print(f"  🏙️ ערים: {', '.join(active_cities) if active_cities else 'אין'}")

        # מחיר
        price_range = config['search_settings']['search_settings'].get('price_range', {})
        if price_range.get('enabled'):
            print(f"  💰 מחיר: {price_range.get('min', 0):,}-{price_range.get('max', 0):,} ₪")
        else:
            print(f"  💰 מחיר: ללא הגבלה")

        # חדרים
        rooms = config['search_settings']['search_settings'].get('rooms', {})
        if rooms.get('enabled'):
            print(f"  🏠 חדרים: {rooms.get('min', 0)}-{rooms.get('max', 0)}")
        else:
            print(f"  🏠 חדרים: ללא הגבלה")

    else:
        print(f"  ❌ config.json לא נמצא")
        all_good = False

    print()

    # 3. בדיקת AI
    print("🤖 חיבור AI:")
    # API key נמצא בקובץ .env או במשתנה סביבה
    api_key_found = False

    # בדיקה 1: משתנה סביבה
    env_api_key = os.getenv('ANTHROPIC_API_KEY')
    if env_api_key:
        masked_key = env_api_key[:8] + "..." + env_api_key[-4:]
        print(f"  ✅ API key קיים (משתנה סביבה): {masked_key}")
        api_key_found = True

    # בדיקה 2: קובץ .env
    env_path = base_dir / ".env"
    if env_path.exists():
        with open(env_path, 'r') as f:
            env_content = f.read()

        if 'ANTHROPIC_API_KEY' in env_content:
            for line in env_content.split('\n'):
                if line.startswith('ANTHROPIC_API_KEY'):
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        api_key = parts[1].strip().strip('"').strip("'")
                        if api_key and len(api_key) > 10:
                            masked_key = api_key[:8] + "..." + api_key[-4:]
                            print(f"  ✅ API key קיים (קובץ .env): {masked_key}")
                            api_key_found = True
                    break

    if not api_key_found:
        print(f"  ⚠️ ANTHROPIC_API_KEY לא נמצא (AI לא יעבוד)")

    print()

    # 4. בדיקת מסד נתונים
    print("💾 מסד נתונים:")
    db_path = base_dir / "posts.db"
    if db_path.exists():
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # ספירה כללית
            cursor.execute("SELECT COUNT(*) FROM posts")
            total = cursor.fetchone()[0]
            print(f"  ✅ posts.db קיים")
            print(f"  📊 {total:,} פוסטים סה\"כ")

            # ספירה לפי קטגוריות
            print(f"  📁 לפי קטגוריות:")
            for category in ['all', 'my', 'important', 'maybe', 'not_relevant']:
                cursor.execute(f"SELECT COUNT(*) FROM posts WHERE category = ?", (category,))
                count = cursor.fetchone()[0]
                emoji = {'all': '📋', 'my': '⭐', 'important': '🔥', 'maybe': '🤔', 'not_relevant': '🚫'}
                print(f"     {emoji.get(category, '•')} {category}: {count:,}")

            # פוסט אחרון
            cursor.execute("SELECT created_at FROM posts ORDER BY created_at DESC LIMIT 1")
            last_post = cursor.fetchone()
            if last_post:
                print(f"  ⏰ פוסט אחרון: {last_post[0]}")

            conn.close()
        except Exception as e:
            print(f"  ❌ שגיאה בקריאת DB: {e}")
            all_good = False
    else:
        print(f"  ⚠️ posts.db עדיין לא קיים (תקין אם זה ריצה ראשונה)")

    print()

    # סיכום
    if all_good:
        print("✅ כל המערכות תקינות!")
    else:
        print("⚠️ יש בעיות שצריך לתקן")
        return 1

    return 0

if __name__ == "__main__":
    exit(main())

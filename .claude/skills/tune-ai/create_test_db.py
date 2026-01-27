#!/usr/bin/env python3
"""
יוצר posts.db לטסטים עם נתונים לדוגמה
"""

import sqlite3
from datetime import datetime

# יצירת DB
conn = sqlite3.connect('posts_test.db')
cursor = conn.cursor()

# יצירת טבלה
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

# נתוני טסט
test_posts = [
    # 1-3: פוסטים RELEVANT רגילים
    ('test_001', 'דירה 4 חדרים בירושלים קטמון, 7500 שח', 'משה כהן', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'ירושלים', 'קטמון', '7500', '4', '050-1234567', 'דירה רגילה למכירה', 'דירות ירושלים'),
    ('test_002', 'להשכיר דירה בבית שמש נווה שמיר 3 חד 5000', 'יוסי לוי', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'בית שמש', 'נווה שמיר', '5000', '3', '052-9876543', 'דירה להשכרה', 'דירות בית שמש'),
    ('test_003', 'דירת 5 חדרים בבני ברק 8500 שח', 'דוד כהן', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'בני ברק', None, '8500', '5', '053-1112233', 'דירה גדולה', 'דירות בני ברק'),

    # 4-6: פוסטים BROKER עם שמות חברות
    ('test_004', 'דירות למכירה ברחבי הארץ! דורון נכסים בשירותכם 24/7', 'דורון נכסים', datetime.now().isoformat(), 0, 1, 'BROKER', None, None, None, None, '050-1111111', 'מתווך מחפש לקוחות', 'דירות ירושלים'),
    ('test_005', 'נדל"ן פלוס - תיק נכסים ענק, שירות מקצועי', 'נדלן פלוס', datetime.now().isoformat(), 0, 1, 'BROKER', None, None, None, None, '052-2222222', 'חברת תיווך', 'דירות בית שמש'),
    ('test_006', 'Real Estate JF מחפשים לקוחות לדירות יוקרה', 'RE JF', datetime.now().isoformat(), 0, 1, 'BROKER', None, None, None, None, '053-3333333', 'מתווך', 'דירות תל אביב'),

    # 7-9: פוסטים NON_URBAN - יישובים
    ('test_007', 'בית למכירה במושב צור משה, 5 חדרים 1.2 מליון', 'אבי', datetime.now().isoformat(), 0, 0, 'NON_URBAN', 'צור משה', None, '1200000', '5', '054-4444444', 'יישוב קטן', 'דירות באזור'),
    ('test_008', 'דירה ביישוב עמנואל 4 חדרים', 'רחל', datetime.now().isoformat(), 0, 0, 'NON_URBAN', 'עמנואל', None, None, '4', '055-5555555', 'יישוב', 'דירות באזור'),
    ('test_009', 'בית בכפר אדומים להשכרה', 'שרה', datetime.now().isoformat(), 0, 0, 'NON_URBAN', 'כפר אדומים', None, None, None, '056-6666666', 'כפר', 'דירות באזור'),

    # 10-12: פוסטים RELEVANT אבל עם מילות חיפוש (blacklist)
    ('test_010', 'מחפש חדר בירושלים באזור גבעת שאול', 'דני', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'ירושלים', 'גבעת שאול', None, None, '057-7777777', 'מחפש מקום', 'דירות ירושלים'),
    ('test_011', 'מחפשת שותף/ה לדירה בבני ברק', 'מיכל', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'בני ברק', None, None, None, '058-8888888', 'חיפוש שותף', 'דירות בני ברק'),
    ('test_012', 'דרוש מקום לגור באזור בית שמש', 'אלי', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'בית שמש', None, None, None, '059-9999999', 'מחפש', 'דירות בית שמש'),

    # 13-15: פוסטים שסווגו לא נכון - RELEVANT עם מילות מתווך
    ('test_013', 'דירה 4 חדרים להשכרה - דורון נכסים', 'דורון נכסים', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'ירושלים', None, '7000', '4', '050-1010101', 'דירה ספציפית אבל מתווך', 'דירות ירושלים'),
    ('test_014', 'למכירה דירה מהממה - נדל"ן פלוס בלעדי', 'נדלן פלוס', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'בית שמש', None, '900000', '3', '052-2020202', 'דירה אבל מתווך', 'דירות בית שמש'),
    ('test_015', 'דירה בבני ברק 3 חדרים מתווך אמין', 'יעקב', datetime.now().isoformat(), 1, 0, 'RELEVANT', 'בני ברק', None, '6500', '3', '053-3030303', 'דירה עם מילת מתווך', 'דירות בני ברק'),

    # 16-17: NON_URBAN אבל עיר רלוונטית (טעות)
    ('test_016', 'דירה בירושלים קטמון 4 חדרים', 'משה', datetime.now().isoformat(), 0, 0, 'NON_URBAN', 'ירושלים', 'קטמון', '8000', '4', '054-1231234', 'סומן בטעות', 'דירות ירושלים'),
    ('test_017', 'דירה בבית שמש רמת בית שמש', 'שלמה', datetime.now().isoformat(), 0, 0, 'NON_URBAN', 'בית שמש', 'רמת בית שמש', '5500', '3', '055-2342345', 'סומן בטעות', 'דירות בית שמש'),

    # 18-19: BROKER ללא סימני תיווך ברורים
    ('test_018', 'יש לי דירה למכירה בירושלים', 'אנונימי', datetime.now().isoformat(), 0, 1, 'BROKER', 'ירושלים', None, None, None, None, 'AI חשב שזה מתווך', 'דירות ירושלים'),
    ('test_019', 'מוכר דירה בבני ברק', 'פלוני', datetime.now().isoformat(), 0, 1, 'BROKER', 'בני ברק', None, None, None, None, 'AI חשב שזה מתווך', 'דירות בני ברק'),

    # 20: פוסט מעיר לא רלוונטית (תל אביב)
    ('test_020', 'דירה 3 חדרים בתל אביב דיזנגוף 9000 שח', 'רוני', datetime.now().isoformat(), 0, 0, 'NON_URBAN', 'תל אביב', 'דיזנגוף', '9000', '3', '050-9999999', 'עיר לא רלוונטית', 'דירות תל אביב'),
]

# הכנס נתונים
cursor.executemany('''
INSERT OR REPLACE INTO posts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
''', test_posts)

conn.commit()
conn.close()

print("✅ נוצר posts_test.db עם 20 פוסטים לטסטים")

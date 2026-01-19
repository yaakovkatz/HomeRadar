from database import PostDatabase
import re

db = PostDatabase()

print("=" * 70)
print("🔍 Debug - בדיקת Regex")
print("=" * 70)

# 1. בדיקה: האם cities_regex קיים?
print(f"\n1. cities_regex קיים? {db.cities_regex is not None}")

if db.cities_regex:
    print(f"2. Pattern: {db.cities_regex.pattern[:100]}...")

# 2. בדיקה ידנית של הפטרן
content = "דירה בירושלים"
print(f"\n3. טקסט לבדיקה: '{content}'")

# נסה את הפטרנים ידנית
if db.cities_regex:
    # פטרן 1: ב + עיר
    pattern1 = rf'ב\s*({db.cities_regex.pattern})(?:\s|,|$)'
    match1 = re.search(pattern1, content, re.IGNORECASE)
    print(f"4. Pattern 'ב + עיר': {match1.group(1) if match1 else 'לא נמצא'}")

    # פטרן 2: רק עיר
    pattern2 = db.cities_regex.pattern
    match2 = re.search(pattern2, content, re.IGNORECASE)
    print(f"5. Pattern 'עיר בלבד': {match2.group(0) if match2 else 'לא נמצא'}")

# 3. מה extract_details מחזיר?
result = db.extract_details(content)
print(f"\n6. extract_details מחזיר: city={result['city']}")

print("=" * 70)
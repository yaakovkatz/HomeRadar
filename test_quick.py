# test_quick.py
from database import PostDatabase

db = PostDatabase()

# טסט 1: האם תופס עיר?
test1 = db.extract_details("דירה בירושלים")
print(f"1. 'בירושלים' → city={test1['city']}")

# טסט 2: האם תופס "הדר" מ"נהדרת"?
test2 = db.extract_details("דירה נהדרת")
print(f"2. 'נהדרת' → city={test2['city']}")

# טסט 3: האם תופס שכונה בטעות?
test3 = db.extract_details("מיקום מרכזי מאוד")
print(f"3. 'מרכזי' → city={test3['city']}, location={test3['location']}")
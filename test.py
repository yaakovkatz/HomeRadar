import re


def test_word_boundary():
    # בדיקות
    texts = [
        ('הדר', 'הדר הכרמל', True),  # ✅
        ('הדר', 'בהדר חיפה', True),  # ✅
        ('הדר', 'שכונת הדר', True),  # ✅
        ('הדר', 'נהדר', False),  # ✅ לא יתפוס!
        ('כרמל', 'כרמל', True),  # ✅
        ('כרמל', 'מרכזית', False),  # ✅ לא יתפוס!
    ]

    for word, text, expected in texts:
        result = bool(re.search(r'\b' + re.escape(word) + r'\b', text))
        status = "✅" if result == expected else "❌"
        print(f"{status} '{word}' ב-'{text}' → {result} (צפוי: {expected})")


test_word_boundary()
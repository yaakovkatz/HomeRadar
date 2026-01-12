"""
ai_agents.py - AI Agents for post classification and data extraction
Agent 1: Classification (RELEVANT/SPAM/BROKER/etc) - with image support
Agent 2: Extraction (fill missing price/city)
"""

import os
import json
from anthropic import Anthropic
from dotenv import load_dotenv
import time


# טעינת API Key מ-.env
load_dotenv()


class AIAgents:
    def __init__(self):
        """Initialize AI Agents with Anthropic API"""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError("❌ ANTHROPIC_API_KEY לא נמצא בקובץ .env")

        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"  # Sonnet 4

        self.last_call = 0
        self.min_delay = 0.5  # 500ms בין קריאות

        print("✅ AI Agents initialized successfully")

    def _wait_if_needed(self):
        """ממתין אם עברו פחות מ-500ms מהקריאה האחרונה"""
        now = time.time()
        elapsed = now - self.last_call
        if elapsed < self.min_delay:
            time.sleep(self.min_delay - elapsed)
        self.last_call = time.time()

    # =========================================================
    # Agent 1: Classification (סינון) - עם תמיכה בתמונות
    # =========================================================

    def classify_post(self, content, author, images=None):
        """
        Agent 1: מסווג פוסט לקטגוריה (עם תמיכה בתמונות!)

        Args:
            content: תוכן הפוסט
            author: שם המפרסם
            images: רשימת URLs של תמונות (אופציונלי)

        Returns:
            {
                'category': 'RELEVANT' | 'BROKER' | 'SPAM' | 'AUCTION' | 'WANTED' | 'QUESTION',
                'is_broker': True/False,
                'confidence': 0.0-1.0,
                'reason': 'הסבר קצר'
            }
        """

        self._wait_if_needed()

        prompt = f"""אתה מומחה לסיווג פוסטים בקבוצות פייסבוק של דירות יד שנייה.

{"קרא את התמונות והפוסט" if images else "קרא את הפוסט הבא"} וסווג אותו לאחת מהקטגוריות:

**RELEVANT** - דירה למכירה/השכרה (רלוונטי!)
- יש תיאור דירה (חדרים, מטר, קומה וכו')
- יכול להיות עם או בלי מחיר
- יכול להיות ממתווך או מבעלים

**AUCTION** - מכרז/כונס נכסים/מכירה פומבית
- תמונה או טקסט עם "כונס נכסים", "מכרז", "הזמנה להציע הצעות"
- מכירה פומבית, רכישת זכויות

**BROKER** - מתווך מחפש לקוחות (לא דירה ספציפית!)
- כתוב "מחפש לקוחות", "תיק נכסים", "שירות תיווך"
- אין תיאור דירה ספציפית

**SPAM** - פרסום לא קשור
- שיפוצים, נקיון, הובלות (בתמונה או בטקסט)
- לא קשור לדירות

**WANTED** - מחפש דירה (לא מוכר!)
- "מחפש דירה", "דרוש", "צריך"

**QUESTION** - שאלה
- "מישהו יודע?", "איך...?", "עזרה"

---

**פוסט:**
מפרסם: {author}
תוכן: {content[:500]}
{"תמונות: מצורפות (קרא אותן!)" if images else ""}

---

**חשוב - תמונות:**
- אם יש תמונה עם "כונס נכסים", "מכרז", "הזמנה להציע הצעות" → AUCTION
- אם יש תמונה של פרסום (הובלות, שיפוצים, נקיון) → SPAM
- קרא את התמונות בקפידה!

---

**החזר תשובה ב-JSON בדיוק בפורמט הזה (ללא טקסט נוסף):**
{{
    "category": "RELEVANT",
    "is_broker": false,
    "confidence": 0.95,
    "reason": "דירה למכירה עם תיאור מפורט"
}}

**כללים:**
1. אם זו דירה ממתווך → category: "RELEVANT", is_broker: true
2. אם מתווך מחפש לקוחות → category: "BROKER", is_broker: true
3. אם מכרז/כונס נכסים → category: "AUCTION", is_broker: false
4. confidence: 0.5-1.0 (עד כמה אתה בטוח)
5. אם confidence < 0.5 → category: "RELEVANT" (במקרה ספק)
"""

        try:
            # בניית message עם תמונות
            message_content = []

            # אם יש תמונות - הוסף אותן קודם
            if images:
                for image_url in images:
                    message_content.append({
                        "type": "image",
                        "source": {
                            "type": "url",
                            "url": image_url
                        }
                    })

            # הוסף את הטקסט
            message_content.append({
                "type": "text",
                "text": prompt
            })

            # שלח ל-Claude
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
                temperature=0,
                messages=[{"role": "user", "content": message_content}]
            )

            # חילוץ התשובה
            result_text = response.content[0].text.strip()

            # ניקוי markdown backticks אם יש
            result_text = result_text.replace('```json', '').replace('```', '').strip()

            # המרה ל-JSON
            result = json.loads(result_text)

            # ולידציה
            if result['confidence'] < 0.5:
                result['category'] = 'RELEVANT'  # במקרה ספק

            return result

        except Exception as e:
            print(f"❌ Agent 1 failed: {e}")
            # ברירת מחדל: נניח שזה רלוונטי
            return {
                'category': 'RELEVANT',
                'is_broker': False,
                'confidence': 0.5,
                'reason': f'AI failed: {str(e)}'
            }

    # =========================================================
    # Agent 2: Extraction (חילוץ)
    # =========================================================

    def extract_missing_details(self, content, regex_found):
        """
        Agent 2: ממלא פרטים חסרים (מחיר, עיר)

        Args:
            content: תוכן הפוסט
            regex_found: מה ש-Regex כבר מצא
                {
                    'price': '7200' | None,
                    'city': 'ירושלים' | None,
                    'rooms': '4' | None,
                    'phone': '050...' | None
                }

        Returns:
            {
                'price': '7200' | None,  # רק אם Regex לא מצא
                'city': 'ירושלים' | None  # רק אם Regex לא מצא
            }
        """

        self._wait_if_needed()

        # מה חסר?
        missing = []
        if not regex_found.get('price'):
            missing.append('מחיר')
        if not regex_found.get('city'):
            missing.append('עיר/מיקום')

        if not missing:
            # אין מה למלא!
            return {'price': None, 'city': None}

        missing_str = ', '.join(missing)

        prompt = f"""אתה מומחה לחילוץ מידע מפוסטים בעברית.

        קרא את הפוסט הבא וחלץ את הפרטים החסרים: **{missing_str}**

        **פוסט:**
        {content[:800]}
        
                ---
        
               **הנחיות:**
        1. **מחיר**: רק מספר (בלי פסיקים/סימנים). אם אין מחיר →    null
        2. **עיר/מיקום**: 
           - חפש עיר, שכונה, או רחוב **בישראל בלבד**
           - אם יש שם עיר או שכונה בישראל → החזר את זה (עדיפות ראשונה!)
           - אם אין עיר/שכונה אבל יש רחוב → החזר את שם הרחוב
           - ערים מחוץ לישראל (כמו "דארטמות'", "לונדון", "ניו יורק") → null
           - אם לא ברור בכלל → null
        3. **אל תמציא!** אם אין מידע → null
        
               **דוגמאות:**
        - "7200 שח" → price: "7200"
        - "בין 2000-2500" → price: "2000"
        - "דירה בירושלים" → city: "ירושלים"
        - "דירה בקטמון" → city: "קטמון"
        - "דירה ברחוב הרצל" → city: "רחוב הרצל"
        - "דירה ברחוב יוסף נדבה" → city: "רחוב יוסף נדבה"
        - "דירה ברחוב יוסף נדבה, ירושלים" → city: "ירושלים"
        - "דירה במרכז העיר דארטמות'" → city: null
        - "דירה בלונדון" → city: null
        - "דירה בצפון" → city: null (לא ספציפי)
        - "מיקום מעולה" → city: null (אין מידע)
        ```
**החזר תשובה ב-JSON בדיוק בפורמט הזה (ללא טקסט נוסף):**
{{
    "price": "7200",
    "city": "ירושלים"
}}

אם אין מידע → השתמש ב-null
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=150,
                temperature=0,
                messages=[{"role": "user", "content": prompt}]
            )

            # חילוץ התשובה
            result_text = response.content[0].text.strip()

            # ניקוי markdown backticks
            result_text = result_text.replace('```json', '').replace('```', '').strip()

            # המרה ל-JSON
            result = json.loads(result_text)

            # ולידציה: רק מחזירים מה שהיה חסר
            output = {}
            if not regex_found.get('price'):
                output['price'] = result.get('price')
            if not regex_found.get('city'):
                output['city'] = result.get('city')

            return output

        except Exception as e:
            print(f"❌ Agent 2 failed: {e}")
            return {'price': None, 'city': None}
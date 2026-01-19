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

**חשוב - תגובות:**
- הטקסט עלול להכיל תגובות של אנשים אחרים (כמו "משה: תגובתי מאוד!")
- **התעלם לגמרי מתגובות!**
- התמקד **רק בתוכן המקורי** של הפוסט
- תגובות מתחילות לרוב בשם אדם + "תגובתי", "מה זה", "יקר מדי" וכו'
- אם יש תיאור דירה בפוסט המקורי → RELEVANT (גם אם יש תגובה שאלה!)

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
        Agent 2: ממלא פרטים חסרים (מחיר, עיר, מיקום)

        Args:
            content: תוכן הפוסט
            regex_found: מה ש-Regex כבר מצא
                {
                    'price': '7200' | None,
                    'city': 'ירושלים' | None,
                    'location': 'פסגת זאב' | None,
                    'rooms': '4' | None,
                    'phone': '050...' | None
                }

        Returns:
            {
                'price': '7200' | None,
                'city': 'ירושלים' | None,
                'location': 'פסגת זאב' | None
            }
        """

        self._wait_if_needed()

        # מה חסר?
        missing = []
        if not regex_found.get('price'):
            missing.append('מחיר')
        if not regex_found.get('city'):
            missing.append('עיר')
        if not regex_found.get('location'):  # ← הוסף את זה!
            missing.append('מיקום (שכונה/רחוב)')

        if not missing:
            # אין מה למלא!
            return {'price': None, 'city': None, 'location': None}

        missing_str = ', '.join(missing)

        prompt = f"""אתה מומחה לחילוץ מידע מפוסטים בעברית.

    קרא את הפוסט הבא וחלץ את הפרטים החסרים: **{missing_str}**

    **פוסט:**
    {content[:800]}

    ---

    **הנחיות קריטיות:**

1. **מחיר (מחיר הדירה בלבד!)**: 
   - חפש מחיר של הדירה עצמה
   - **התעלם ממחירים של:** מטבח, שיפוץ, ארונות, רהיטים, השקעה
   - דוגמאות לא נכונות: "מטבח 100,000", "שיפוץ 50,000"
   - אם אין מחיר דירה → null3
   
   2. **עיר:**
   - חפש עיר מפורשת: "בירושלים", "תל אביב", "חיפה"
   - **אל תמציא! אם לא כתוב עיר מפורש → null**
   
3. **מיקום (שכונה/רחוב) - קריטי!**
   - **זה השדה הכי חשוב - תמיד חפש אותו!**
   - חפש שכונה ו/או רחוב בפוסט
   
   **דוגמאות לשכונות:**
   - ירושלים: קטמון, קריית יובל, פסגת זאב, גבעת שאול, תלפיות, ארנונה
   - תל אביב: דיזנגוף, פלורנטין, נווה צדק, רמת אביב
   
   **דוגמאות לרחובות:**
   - "רחוב הרצל", "רח' בן יהודה", "דרך בגין"
   
   **כללים:**
   - אם יש **רק שכונה** → החזר שכונה
   - אם יש **רק רחוב** → החזר רחוב
   - אם יש **גם שכונה וגם רחוב** → החזר את שניהם בפורמט: "שכונה, רחוב"
   - אם באמת אין → null
   
   **דוגמאות:**
   - "דירה בקריית יובל, רחוב ז'בוטינסקי" → location: "קריית יובל, רחוב ז'בוטינסקי"
   - "דירה בקריית יובל" → location: "קריית יובל"
   - "דירה ברחוב הרצל" → location: "רחוב הרצל"
   - "דירה בירושלים" → location: null
   
         **חשוב:** גם אם אין עיר, אם יש רחוב - החזר אותו ב-location!
דוגמה: "דירה ברחוב הארזים 12" → city: null, location: "רחוב הארזים"         

    4. **כלל זהב: אם לא בטוח → null**

    ---

    **חשוב - תגובות:**
    - הטקסט עלול להכיל תגובות של אנשים אחרים
    - **חלץ מידע רק מהפוסט המקורי, התעלם לגמרי מתגובות!**
    - דוגמה: אם בפוסט כתוב "7000 שח" ובתגובה "אני מוכן 5000" → החזר "7000"
    - דוגמה: אם בפוסט כתוב "בירושלים" ובתגובה "יש גם בתל אביב?" → החזר "ירושלים"

    ---

    **דוגמאות חשובות:**

    ✅ "דירה בירושלים ברחוב הרצל" 
       → city: "ירושלים", location: "רחוב הרצל"

    ✅ "דירה בפסגת זאב ברחוב אלי תבין" 
       → city: "ירושלים", location: "פסגת זאב" (שכונה ידועה)

    ❌ "דירה ברחוב הרצל" 
       → city: null, location: null (אין עיר!)

    ❌ "דירה ברחוב דיזנגוף" 
       → city: null, location: null (גם אם דיזנגוף ידוע - לא נכתב "תל אביב"!)
       
               **דוגמאות מחיר:**
        
        ✅ "דירה למכירה 2,500,000 ש״ח" → price: "2500000"
        ✅ "מחיר מבוקש: 3.5 מיליון" → price: "3500000"
        ❌ "מטבח חדש 100,000 ש״ח" → price: null (זה מחיר מטבח!)
        ❌ "השקענו 200,000 בשיפוצים" → price: null (זה שיפוץ!)
        ❌ "ארונות בהתאמה 80,000" → price: null (זה ריהוט!)
        
        **אם יש גם מחיר דירה וגם מחירים של שדרוגים - קח רק את מחיר הדירה!**
        דוגמה: "דירה 2,800,000 ש״ח, מטבח 100,000" → price: "2800000"
        
            ---

    **החזר תשובה ב-JSON בדיוק בפורמט הזה (ללא טקסט נוסף):**
    {{
        "price": "7200",
        "city": "ירושלים",
        "location": "פסגת זאב"
    }}

    אם אין מידע → השתמש ב-null
    """

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=200,
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

            if not regex_found.get('location'):
                output['location'] = result.get('location')

            return output

        except Exception as e:
            print(f"❌ Agent 2 failed: {e}")
            return {'price': None, 'city': None, 'location': None}
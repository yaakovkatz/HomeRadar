---
name: validate-setup
description: Validates that HomeRadar system is properly configured and all components are loaded correctly. Use when you need to quickly check system health.
---

# Validate Setup Skill

Performs comprehensive system validation for the HomeRadar real estate monitoring application.

## What to Check

### 1. Streets Database (Government Data)
- Check if `streets.csv` exists and is loaded
- Report number of streets in database
- Report number of cities in database
- Show sample cities from database

### 2. Broker Keywords Configuration
- Check if broker keywords are loaded from config
- Report how many broker keywords are configured
- Show first few broker keywords as examples
- **CRITICAL**: Verify the nested path is correct (`search_settings.search_settings.broker_keywords`)

### 3. Whitelist/Blacklist
- Check if whitelist is configured and how many terms
- Check if blacklist is configured and how many terms
- **CRITICAL**: Verify nested paths are correct

### 4. AI Connection
- Check if AI agents are initialized
- Verify API key is present (don't show the actual key)
- Check AI model configuration

### 5. Database
- Check if `listings.db` exists
- Report total number of posts in database
- Report how many posts in each category (all/my/important/maybe/not_relevant)
- Show most recent post timestamp

### 6. Active Filters
- Show which cities are being monitored
- Show active neighborhoods per city
- Show price range filters
- Show room filters

## How to Execute

1. **Read Configuration**: Read `config.json` to check all settings
   - Pay special attention to nested paths: `search_settings.search_settings.*`

2. **Check Streets Database**:
   ```python
   import os
   streets_path = os.path.join('/home/user/HomeRadar', 'streets.csv')
   # Check if file exists
   # Count lines
   # Parse cities (column 4)
   ```

3. **Check Database**:
   ```python
   import sqlite3
   db_path = '/home/user/HomeRadar/listings.db'
   # Connect and query
   ```

4. **Present Results**: Show clear summary with ✅/❌ for each component

## Output Format

Present results as:

```
🔍 בדיקת מערכת HomeRadar

📊 מאגר רחובות ממשלתי:
  ✅ streets.csv נטען בהצלחה
  📈 40,140 רחובות
  🏙️ 134 ערים
  📍 דוגמאות: ירושלים, תל אביב-יפו, בני ברק...

🚫 מילות מפתח מתווכים:
  ✅ broker_keywords נטען
  📋 20 מילות מפתח
  🔑 דוגמאות: מתווך, תיווך, רישיון תיווך...

🤖 חיבור AI:
  ✅ API key קיים
  🎯 מודל: claude-sonnet-4-5...

💾 מסד נתונים:
  ✅ listings.db קיים
  📊 1,234 פוסטים סה"כ
  📁 לפי קטגוריות:
     - הכל: 1,234
     - שלי: 45
     - חשוב: 12
     - אולי: 89
     - לא רלוונטי: 1,088

🎯 פילטרים פעילים:
  🏙️ ערים: ירושלים, בית שמש, בני ברק
  📍 שכונות בירושלים: רמות, גילה, פסגת זאב...
  💰 מחיר: 3,000-7,000 ₪
  🏠 חדרים: 3-5
```

## Error Handling

If any component fails:
- ❌ Show clear error message
- 🔧 Suggest how to fix it
- 📝 Show the exact path/file that's missing

## When to Use This Skill

Use `/validate-setup` when:
- Starting a work session
- After making configuration changes
- When something seems broken
- When broker filtering isn't working
- When street validation seems off
- Before deploying changes

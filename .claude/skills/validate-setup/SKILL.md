---
name: validate-setup
description: Validates that HomeRadar system is properly configured and all components are loaded correctly. Use when you need to quickly check system health.
---

# Validate Setup Skill

Performs comprehensive system validation for the HomeRadar real estate monitoring application.

## What This Skill Does

Runs the `validate_setup.py` script which automatically checks all system components:

- ✅ **Streets database** - Government data from streets.csv (counts streets and cities dynamically)
- ✅ **Broker keywords** - Validates nested config path and counts keywords
- ✅ **Whitelist/Blacklist** - Reports current counts
- ✅ **AI connection** - Checks for ANTHROPIC_API_KEY in environment or .env file
- ✅ **Database** - Verifies posts.db exists and shows category counts
- ✅ **Active filters** - Shows which cities, price ranges, and room filters are enabled

**Why use the script?** It's **self-updating** - reads the current configuration dynamically, so it always shows accurate counts even when the user adds new keywords or settings.

## How to Execute

Simply run the validation script:

```bash
python3 validate_setup.py
```

That's it! The script handles everything automatically.

## What to Do After Running

1. **Show the user the complete output** from the script (it's already nicely formatted in Hebrew with emojis)

2. **If there are errors (❌ or ⚠️)**, offer to help fix them:
   - `❌ קובץ .env לא קיים` → Explain the user needs to create a .env file with their ANTHROPIC_API_KEY
   - `❌ streets.csv לא נמצא` → Check if the file was moved or deleted
   - `❌ שגיאה בקריאת DB` → Investigate database schema issues
   - `⚠️ posts.db עדיין לא קיים` → This is normal if they haven't run the scraper yet

3. **If everything is ✅**, confirm the system is healthy and ready

## When to Use This Skill

Use `/validate-setup` when:
- Starting a work session
- After making configuration changes (added broker keywords, cities, etc.)
- When something seems broken (broker filtering, street validation, AI agents)
- Before deploying changes or pushing code
- User reports unexpected behavior

## Notes

- The script is located at `/home/user/HomeRadar/validate_setup.py`
- It requires no arguments or parameters
- Runtime is typically < 1 second
- Output is in Hebrew with clear emoji indicators (✅ = good, ❌ = error, ⚠️ = warning)

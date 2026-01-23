#!/bin/bash
# Handler for /tune-ai skill

# Get arguments passed to the skill
ARGS="$@"

# Change to project directory
cd /home/user/HomeRadar

echo "======================================================================="
echo "🎯 /tune-ai Skill"
echo "======================================================================="
echo ""

# רוץ טסטים אוטומטיים תחילה (אם אין --skip-tests)
if [[ ! "$ARGS" =~ "--skip-tests" ]]; then
    echo "🧪 מריץ טסטים אוטומטיים..."
    echo "-----------------------------------------------------------------------"
    python3 test_tune_ai.py
    TEST_EXIT_CODE=$?

    if [ $TEST_EXIT_CODE -ne 0 ]; then
        echo ""
        echo "❌ טסטים נכשלו! בודק את המערכת."
        exit 1
    fi

    echo ""
    echo "✅ כל הטסטים עברו בהצלחה!"
    echo "======================================================================="
    echo ""
fi

# הרץ את tune_ai עם הארגומנטים
python3 tune_ai.py $ARGS

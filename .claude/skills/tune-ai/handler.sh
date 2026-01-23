#!/bin/bash
# Handler for /tune-ai skill

# Get arguments passed to the skill
ARGS="$@"

# Get the directory where this script is located (the skill directory)
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="/home/user/HomeRadar"

echo "======================================================================="
echo "🎯 /tune-ai Skill"
echo "======================================================================="
echo ""

# רוץ טסטים אוטומטיים תחילה (אם אין --skip-tests)
if [[ ! "$ARGS" =~ "--skip-tests" ]]; then
    echo "🧪 מריץ טסטים אוטומטיים..."
    echo "-----------------------------------------------------------------------"
    cd "$PROJECT_DIR"
    python3 "$SKILL_DIR/test_tune_ai.py"
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
cd "$PROJECT_DIR"
python3 "$SKILL_DIR/tune_ai.py" $ARGS

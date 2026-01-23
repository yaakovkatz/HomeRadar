#!/bin/bash
# Handler for /tune-ai skill

# Get arguments passed to the skill
ARGS="$@"

# Run the tune_ai.py script with arguments
cd /home/user/HomeRadar
python3 tune_ai.py $ARGS

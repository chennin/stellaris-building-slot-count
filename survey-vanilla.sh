#!/bin/bash
find ~/stellaris-game/ -type f -name "*.txt" -exec ./look_for_add.py '{}' \; | sort -k 2,3 | column -t | tee vanilla_survey.txt

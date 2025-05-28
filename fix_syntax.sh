#!/bin/bash

# Backup the original file
cp layouts/smart_locks.py layouts/smart_locks.py.bak3

# Extract the problematic section
sed -n '1825,1840p' layouts/smart_locks.py

# Fix the indentation using sed
sed -i '' '1830s/^.*# Marcar/                    # Marcar/g' layouts/smart_locks.py
sed -i '' '1831s/^.*for sensor/                    for sensor/g' layouts/smart_locks.py

echo "Fixed indentation at lines 1830-1831"

# Show the fixed section
echo "Fixed section:"
sed -n '1825,1840p' layouts/smart_locks.py 
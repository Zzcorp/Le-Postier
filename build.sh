#!/bin/bash
# fix_postcards.sh
# Run this script to fix all postcard issues

echo "=============================================="
echo "POSTCARD COLLECTION FIX SCRIPT"
echo "=============================================="

# Step 1: Run diagnostic
echo ""
echo "Step 1: Running diagnostic..."
python manage.py full_media_diagnostic --verbose

# Step 2: Ask for CSV/SQL file location
echo ""
echo "Step 2: Import data"
read -p "Enter path to your CSV or SQL file: " DATA_FILE

if [ -f "$DATA_FILE" ]; then
    echo "Importing data from: $DATA_FILE"
    python manage.py import_data_complete "$DATA_FILE" --update
else
    echo "File not found: $DATA_FILE"
fi

# Step 3: Update postcard flags
echo ""
echo "Step 3: Updating postcard flags..."
python manage.py update_postcard_flags

# Step 4: Final diagnostic
echo ""
echo "Step 4: Final diagnostic..."
python manage.py full_media_diagnostic

echo ""
echo "=============================================="
echo "COMPLETE"
echo "=============================================="
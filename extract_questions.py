#!/usr/bin/env python3
"""
Question Extraction Utility Script

This script extracts questions from the SQLite database ('questions' table)
and saves them into a JSON file containing only the questions (and no other fields).

Usage:
    python extract_questions.py [options]

Examples:
    # Save to default 'questions.json' as a flat array of strings, excluding bad questions
    python extract_questions.py

    # Save to a custom path as an array of JSON objects: [{"question": "..."}]
    python extract_questions.py -o custom_questions.json -f object

    # Include bad (flagged) questions as well
    python extract_questions.py --include-bad
"""

import os
import sys
import json
import sqlite3
import argparse
from pathlib import Path

# Add project root to path to resolve any internal imports if needed
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJECT_ROOT))

def get_db_path() -> Path:
    """
    Resolves the database path using src.config if available,
    falling back to the default relative data/db.sqlite path.
    """
    try:
        from src import config
        if hasattr(config, 'DB_PATH') and config.DB_PATH.exists():
            return Path(config.DB_PATH)
    except ImportError:
        pass
    
    # Fallback to default path relative to script root
    fallback_path = PROJECT_ROOT / "data" / "db.sqlite"
    return fallback_path

def main():
    parser = argparse.ArgumentParser(
        description="Extract questions from the database into a JSON file."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="questions.json",
        help="Path to the output JSON file (default: questions.json)"
    )
    parser.add_argument(
        "-f", "--format",
        choices=["flat", "object"],
        default="flat",
        help="Output JSON structure: 'flat' for string array, 'object' for dictionary array (default: flat)"
    )
    parser.add_argument(
        "--include-bad",
        action="store_true",
        help="Include questions flagged as 'bad_question' (default: false)"
    )
    parser.add_argument(
        "--no-pretty",
        action="store_true",
        help="Do not pretty-print the JSON output (saves space)"
    )
    
    args = parser.parse_args()
    
    db_path = get_db_path()
    if not db_path.exists():
        print(f"❌ Error: Database file not found at '{db_path}'.", file=sys.stderr)
        print("Please make sure you are running this script in the root directory or that your database is initialized.", file=sys.stderr)
        sys.exit(1)
        
    print(f"📂 Found database at: {db_path}")
    
    try:
        # Connect to SQLite database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if bad_question column exists in schema
        cursor.execute("PRAGMA table_info(questions)")
        columns = [col[1] for col in cursor.fetchall()]
        has_bad_question_col = "bad_question" in columns
        
        # Build SQL query
        query = "SELECT question_text FROM questions"
        params = []
        
        if has_bad_question_col and not args.include_bad:
            query += " WHERE bad_question = 0"
            print("💡 Filtering out questions marked as 'bad' (bad_question = 1).")
        elif not has_bad_question_col:
            print("⚠️ Note: 'bad_question' column not found in database schema. Extracting all questions.")
            
        query += " ORDER BY id ASC"
        
        # Execute query
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # Extract questions
        questions = [row[0] for row in rows if row[0]]
        
        total_questions = len(questions)
        print(f"🔍 Extracted {total_questions} questions from the database.")
        
        if total_questions == 0:
            print("⚠️ Warning: No questions found to extract.")
            
        # Format the output data
        if args.format == "flat":
            output_data = questions
        else:
            output_data = [{"question": q} for q in questions]
            
        # Determine output file path
        output_path = Path(args.output).resolve()
        
        # Ensure parent directories exist
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write to JSON file
        indent = None if args.no_pretty else 2
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, ensure_ascii=False, indent=indent)
            
        print(f"✅ Success! Saved {total_questions} questions to '{output_path}'.")
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()

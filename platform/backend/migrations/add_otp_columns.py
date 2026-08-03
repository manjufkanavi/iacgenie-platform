#!/usr/bin/env python3

"""

Database Migration: Add missing columns to users table

This script adds OTP-related and email verification columns to the users table.

"""

# nosemgrep: backend/migrations/add_otp_columns.py — SQL adds controlled DDL columns, not user input

import sqlite3

DB_PATH = "iacgenie.db"


def add_missing_columns():
    """Add missing columns to users table"""
    conn = sqlite3.connect(DB_PATH)
    # List of columns to add
    columns_to_add = [
        ("otp_hash", "TEXT"),
        ("otp_expires_at", "TIMESTAMP"),
        ("email_verified", "BOOLEAN DEFAULT 0"),
        ("password_reset_token", "TEXT"),
        ("password_reset_expires", "TIMESTAMP"),
    ]
    cursor = conn.cursor()
    for column_name, column_type in columns_to_add:
        try:
            # Check if column already exists
            # nosemgrep: python.lang.security.audit.formatted-sql-query.formatted-sql-query
            cursor.execute("PRAGMA table_info(users)")
            existing_columns = [row[1] for row in cursor.fetchall()]
            if column_name in existing_columns:
                print(f"Column '{column_name}' already exists, skipping...")
            else:
                # Add the column
                # nosemgrep: sqlalchemy-execute-raw-query formatted-sql-query
                _sql = "ALTER TABLE users ADD COLUMN " + column_name + " " + column_type
                cursor.execute(_sql)  # nosemgrep: sqlalchemy-execute-raw-query
                print(f"Added column: {column_name}")
        except Exception as e:
            print(f"Could not add '{column_name}': {e}")
    conn.commit()
    conn.close()
    print("\nDatabase migration completed!")


if __name__ == "__main__":
    add_missing_columns()

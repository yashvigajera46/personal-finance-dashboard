import sqlite3
import pandas as pd
import os

DB_NAME = "finance.db"
RECEIPTS_DIR = "receipts"

# Ensure receipts folder exists
if not os.path.exists(RECEIPTS_DIR):
    os.makedirs(RECEIPTS_DIR)

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # 1. Transactions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            type TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            description TEXT,
            payment_method TEXT DEFAULT 'Cash',
            tags TEXT DEFAULT '',
            receipt_path TEXT DEFAULT ''
        )
    """)

    # Schema Migration: dynamically add missing columns without losing existing records
    cursor.execute("PRAGMA table_info(transactions)")
    existing_cols = [col[1] for col in cursor.fetchall()]

    if "currency" not in existing_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN currency TEXT DEFAULT 'INR'")
    if "payment_method" not in existing_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN payment_method TEXT DEFAULT 'Cash'")
    if "tags" not in existing_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN tags TEXT DEFAULT ''")
    if "receipt_path" not in existing_cols:
        cursor.execute("ALTER TABLE transactions ADD COLUMN receipt_path TEXT DEFAULT ''")
    
    # 2. Custom Categories Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS custom_categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            type TEXT NOT NULL
        )
    """)

    # 3. Category Budgets Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS category_budgets (
            category TEXT PRIMARY KEY,
            budget_limit REAL NOT NULL
        )
    """)

    # 4. Recurring Subscriptions Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT DEFAULT 'INR',
            billing_day INTEGER NOT NULL
        )
    """)

    cursor.execute("PRAGMA table_info(subscriptions)")
    sub_cols = [col[1] for col in cursor.fetchall()]
    if "currency" not in sub_cols:
        cursor.execute("ALTER TABLE subscriptions ADD COLUMN currency TEXT DEFAULT 'INR'")

    conn.commit()
    conn.close()

# --- TRANSACTION CRUD FUNCTIONS ---
def add_transaction(date, trans_type, category, amount, currency, description, payment_method, tags, receipt_path=""):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO transactions (date, type, category, amount, currency, description, payment_method, tags, receipt_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (str(date), trans_type, category, float(amount), currency, description, payment_method, tags, receipt_path))
    conn.commit()
    conn.close()

def update_transaction(trans_id, date, trans_type, category, amount, currency, description, payment_method, tags):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE transactions
        SET date = ?, type = ?, category = ?, amount = ?, currency = ?, description = ?, payment_method = ?, tags = ?
        WHERE id = ?
    """, (str(date), trans_type, category, float(amount), currency, description, payment_method, tags, trans_id))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT receipt_path FROM transactions WHERE id = ?", (transaction_id,))
    row = cursor.fetchone()
    if row and row[0] and os.path.exists(row[0]):
        try:
            os.remove(row[0])
        except OSError:
            pass
    cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()

def get_all_transactions():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM transactions ORDER BY date DESC, id DESC", conn)
    conn.close()
    return df

def bulk_insert(dataframe):
    conn = sqlite3.connect(DB_NAME)
    for col in ['currency', 'payment_method', 'tags', 'receipt_path']:
        if col not in dataframe.columns:
            dataframe[col] = 'INR' if col == 'currency' else ''
    cols = ['date', 'type', 'category', 'amount', 'currency', 'description', 'payment_method', 'tags', 'receipt_path']
    dataframe[cols].to_sql('transactions', conn, if_exists='append', index=False)
    conn.close()

# --- CUSTOM CATEGORIES ---
def add_custom_category(name, cat_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO custom_categories (name, type) VALUES (?, ?)", (name.strip(), cat_type))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    conn.close()

def get_custom_categories(cat_type):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM custom_categories WHERE type = ?", (cat_type,))
    cats = [row[0] for row in cursor.fetchall()]
    conn.close()
    return cats

# --- CATEGORY BUDGETS ---
def set_category_budget(category, budget_limit):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO category_budgets (category, budget_limit)
        VALUES (?, ?)
        ON CONFLICT(category) DO UPDATE SET budget_limit = excluded.budget_limit
    """, (category, float(budget_limit)))
    conn.commit()
    conn.close()

def get_category_budgets():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM category_budgets", conn)
    conn.close()
    return df

# --- RECURRING SUBSCRIPTIONS ---
def add_subscription(name, category, amount, currency, billing_day):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO subscriptions (name, category, amount, currency, billing_day)
        VALUES (?, ?, ?, ?, ?)
    """, (name, category, float(amount), currency, int(billing_day)))
    conn.commit()
    conn.close()

def delete_subscription(sub_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM subscriptions WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()

def get_subscriptions():
    conn = sqlite3.connect(DB_NAME)
    df = pd.read_sql_query("SELECT * FROM subscriptions", conn)
    conn.close()
    return df
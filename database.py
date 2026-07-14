import sqlite3
import json
from datetime import datetime

class Database:
    def __init__(self, db_file="bot.db"):
        self.conn = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.create_tables()

    def create_tables(self):
        # Пользователи
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                balance REAL DEFAULT 0,
                requisites TEXT,
                referral_id INTEGER,
                language TEXT DEFAULT 'ru',
                successful_deals INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Сделки
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS deals (
                deal_id TEXT PRIMARY KEY,
                creator_id INTEGER,
                partner_id INTEGER,
                currency TEXT,
                amount REAL,
                description TEXT,
                nft_link TEXT,
                status TEXT DEFAULT 'pending',
                memo TEXT UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            )
        """)
        # Заявки на вывод
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS withdraw_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                requisites TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Обращения в поддержку
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS support_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT,
                admin_reply TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT 0
            )
        """)
        # Реферальные бонусы (для истории)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS referral_bonuses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount REAL,
                from_user_id INTEGER,
                deal_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Для хранения баланса пополнений (можно просто изменять баланс)
        self.conn.commit()

    def get_user(self, user_id):
        self.cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return self.cursor.fetchone()

    def create_user(self, user_id, username, first_name, referral_id=None):
        self.cursor.execute("""
            INSERT OR IGNORE INTO users (user_id, username, first_name, referral_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, referral_id))
        self.conn.commit()

    def update_user(self, user_id, **kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
        self.conn.commit()

    def get_user_balance(self, user_id):
        self.cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def add_balance(self, user_id, amount):
        self.cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
        self.conn.commit()

    def get_user_requisites(self, user_id):
        self.cursor.execute("SELECT requisites FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def set_requisites(self, user_id, requisites):
        self.cursor.execute("UPDATE users SET requisites = ? WHERE user_id = ?", (requisites, user_id))
        self.conn.commit()

    def create_deal(self, deal_id, creator_id, currency, amount, description, nft_link, memo):
        self.cursor.execute("""
            INSERT INTO deals (deal_id, creator_id, currency, amount, description, nft_link, memo)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (deal_id, creator_id, currency, amount, description, nft_link, memo))
        self.conn.commit()
        return deal_id

    def get_deal(self, deal_id):
        self.cursor.execute("SELECT * FROM deals WHERE deal_id = ?", (deal_id,))
        return self.cursor.fetchone()

    def get_deal_by_memo(self, memo):
        self.cursor.execute("SELECT * FROM deals WHERE memo = ?", (memo,))
        return self.cursor.fetchone()

    def update_deal(self, deal_id, **kwargs):
        for key, value in kwargs.items():
            self.cursor.execute(f"UPDATE deals SET {key} = ? WHERE deal_id = ?", (value, deal_id))
        self.conn.commit()

    def get_user_deals(self, user_id):
        self.cursor.execute("""
            SELECT * FROM deals WHERE creator_id = ? OR partner_id = ?
            ORDER BY created_at DESC
        """, (user_id, user_id))
        return self.cursor.fetchall()

    def get_successful_deals_count(self, user_id):
        self.cursor.execute("SELECT successful_deals FROM users WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def increment_successful_deals(self, user_id, count=1):
        self.cursor.execute("UPDATE users SET successful_deals = successful_deals + ? WHERE user_id = ?", (count, user_id))
        self.conn.commit()

    def create_withdraw_request(self, user_id, amount, requisites):
        self.cursor.execute("""
            INSERT INTO withdraw_requests (user_id, amount, requisites)
            VALUES (?, ?, ?)
        """, (user_id, amount, requisites))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_withdraw_requests(self, user_id=None, status=None):
        if user_id:
            self.cursor.execute("SELECT * FROM withdraw_requests WHERE user_id = ?", (user_id,))
        elif status:
            self.cursor.execute("SELECT * FROM withdraw_requests WHERE status = ?", (status,))
        else:
            self.cursor.execute("SELECT * FROM withdraw_requests")
        return self.cursor.fetchall()

    def update_withdraw_request(self, req_id, status):
        self.cursor.execute("UPDATE withdraw_requests SET status = ? WHERE id = ?", (status, req_id))
        self.conn.commit()

    def create_support_ticket(self, user_id, message):
        self.cursor.execute("""
            INSERT INTO support_tickets (user_id, message)
            VALUES (?, ?)
        """, (user_id, message))
        self.conn.commit()
        return self.cursor.lastrowid

    def get_tickets(self, user_id=None, resolved=False):
        if user_id:
            self.cursor.execute("SELECT * FROM support_tickets WHERE user_id = ? AND resolved = ?", (user_id, resolved))
        else:
            self.cursor.execute("SELECT * FROM support_tickets WHERE resolved = ?", (resolved,))
        return self.cursor.fetchall()

    def resolve_ticket(self, ticket_id, admin_reply):
        self.cursor.execute("UPDATE support_tickets SET resolved = 1, admin_reply = ? WHERE id = ?", (admin_reply, ticket_id))
        self.conn.commit()

    def get_referral_bonuses(self, user_id):
        self.cursor.execute("SELECT * FROM referral_bonuses WHERE user_id = ?", (user_id,))
        return self.cursor.fetchall()

    def add_referral_bonus(self, user_id, amount, from_user_id, deal_id):
        self.cursor.execute("""
            INSERT INTO referral_bonuses (user_id, amount, from_user_id, deal_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, amount, from_user_id, deal_id))
        self.conn.commit()

    def close(self):
        self.conn.close()

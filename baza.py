import sqlite3
import os
from datetime import datetime

DB_SCIEZKA = os.path.join(os.path.dirname(__file__), "siec.db")


class BazaDanych:
    def __init__(self):
        self.conn = sqlite3.connect(DB_SCIEZKA, check_same_thread=False)
        self._inicjalizuj()

    def _inicjalizuj(self):
        cur = self.conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS urzadzenia (
                ip                TEXT PRIMARY KEY,
                mac               TEXT,
                nazwa_uzytkownika TEXT,
                pierwsza_wizyta   TEXT,
                ostatnia_wizyta   TEXT
            );
            CREATE TABLE IF NOT EXISTS historia (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                ip        TEXT,
                status    TEXT,
                timestamp TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_historia_ip ON historia(ip);
        """)
        self.conn.commit()

    # ── Urządzenia ────────────────────────────────────────────────────────────

    def czy_nowe(self, ip: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM urzadzenia WHERE ip = ?", (ip,))
        return cur.fetchone() is None

    def zapisz_urzadzenie(self, ip: str, mac: str):
        now = _teraz()
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO urzadzenia (ip, mac, pierwsza_wizyta, ostatnia_wizyta)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(ip) DO UPDATE SET
                mac             = excluded.mac,
                ostatnia_wizyta = excluded.ostatnia_wizyta
        """, (ip, mac, now, now))
        self.conn.commit()

    def pobierz_nazwe(self, ip: str):
        """Zwraca nazwę nadaną przez użytkownika lub None."""
        cur = self.conn.cursor()
        cur.execute("SELECT nazwa_uzytkownika FROM urzadzenia WHERE ip = ?", (ip,))
        row = cur.fetchone()
        return row[0] if row and row[0] else None

    def zapisz_nazwe(self, ip: str, nazwa: str):
        now = _teraz()
        cur = self.conn.cursor()
        cur.execute("""
            INSERT INTO urzadzenia (ip, mac, nazwa_uzytkownika, pierwsza_wizyta, ostatnia_wizyta)
            VALUES (?, '', ?, ?, ?)
            ON CONFLICT(ip) DO UPDATE SET nazwa_uzytkownika = excluded.nazwa_uzytkownika
        """, (ip, nazwa, now, now))
        self.conn.commit()

    def pobierz_info(self, ip: str):
        """Zwraca (mac, nazwa_uzytkownika, pierwsza_wizyta, ostatnia_wizyta) lub None."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT mac, nazwa_uzytkownika, pierwsza_wizyta, ostatnia_wizyta
            FROM urzadzenia WHERE ip = ?
        """, (ip,))
        return cur.fetchone()

    # ── Historia ──────────────────────────────────────────────────────────────

    def dodaj_zdarzenie(self, ip: str, status: str):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT INTO historia (ip, status, timestamp) VALUES (?, ?, ?)",
            (ip, status, _teraz())
        )
        self.conn.commit()

    def pobierz_historie(self, ip: str, limit: int = 60):
        """Zwraca listę (status, timestamp) od najnowszych."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT status, timestamp FROM historia
            WHERE ip = ? ORDER BY id DESC LIMIT ?
        """, (ip, limit))
        return cur.fetchall()

    def ostatni_status(self, ip: str):
        """Zwraca ostatni zapisany status ('online'/'offline') lub None."""
        cur = self.conn.cursor()
        cur.execute("""
            SELECT status FROM historia WHERE ip = ? ORDER BY id DESC LIMIT 1
        """, (ip,))
        row = cur.fetchone()
        return row[0] if row else None


def _teraz() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

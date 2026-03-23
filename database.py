import sqlite3
import threading
from datetime import datetime, timedelta
from typing import List, Optional, Tuple


class Database:
    """Lapisan akses data agar query tidak tersebar di handler Telegram."""

    def __init__(self, db_path: str = "laporan_kerja.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.lock = threading.Lock()
        self._init_schema()

    def _execute(self, query: str, params: tuple = (), commit: bool = False):
        with self.lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params)
            if commit:
                self.conn.commit()
            return cursor

    def _ensure_column_exists(self, table_name: str, column_name: str, column_type: str):
        cursor = self._execute(f"PRAGMA table_info({table_name})")
        existing_columns = [row[1] for row in cursor.fetchall()]
        if column_name not in existing_columns:
            self._execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}",
                commit=True,
            )

    def _init_schema(self):
        self._execute(
            '''
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT UNIQUE,
                job_name TEXT
            );
            ''',
            commit=True,
        )
        self._execute(
            '''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_name TEXT UNIQUE,
                wage REAL,
                description TEXT
            );
            ''',
            commit=True,
        )
        self._execute(
            '''
            CREATE TABLE IF NOT EXISTS tasks_employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                task_id INTEGER,
                qty INTEGER,
                waktu TEXT
            );
            ''',
            commit=True,
        )
        self._execute(
            '''
            CREATE TABLE IF NOT EXISTS presensi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER,
                qty INTEGER,
                waktu TEXT
            );
            ''',
            commit=True,
        )
        self._execute(
            '''
            CREATE TABLE IF NOT EXISTS laporan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tasks_employees_id INTEGER,
                user_id TEXT,
                waktu TEXT
            );
            ''',
            commit=True,
        )

        # Kompatibilitas untuk data lama yang belum punya kolom detail laporan.
        self._ensure_column_exists("laporan", "nama", "TEXT")
        self._ensure_column_exists("laporan", "jenis_input", "TEXT")
        self._ensure_column_exists("laporan", "detail", "TEXT")
        self._ensure_column_exists("laporan", "employee_id", "INTEGER")
        self._ensure_column_exists("laporan", "task_id", "INTEGER")
        self._ensure_column_exists("laporan", "qty", "INTEGER")
        self._ensure_column_exists("laporan", "wage_per_unit", "REAL")
        self._ensure_column_exists("laporan", "week_start", "TEXT")
        self._ensure_column_exists("laporan", "week_end", "TEXT")
        self._ensure_column_exists("laporan", "notes", "TEXT")

        self._execute(
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_employees_unique ON tasks_employees(employee_id, task_id)",
            commit=True,
        )
        self._execute(
            "CREATE INDEX IF NOT EXISTS idx_laporan_week_range ON laporan(week_start, week_end)",
            commit=True,
        )

    def get_employees(self) -> List[Tuple[int, str, str]]:
        cursor = self._execute("SELECT id, nama, job_name FROM employees ORDER BY nama")
        return cursor.fetchall()

    def get_employee_name(self, employee_id: int) -> Optional[str]:
        cursor = self._execute("SELECT nama FROM employees WHERE id=?", (employee_id,))
        row = cursor.fetchone()
        return row[0] if row else None

    def get_employee_id_by_name(self, name: str) -> Optional[int]:
        cursor = self._execute("SELECT id FROM employees WHERE nama=?", (name,))
        row = cursor.fetchone()
        return row[0] if row else None

    def add_employee(self, name: str) -> bool:
        data_pecah = name.split("|")
        if len(data_pecah) < 2:
            return False  # Format tidak sesuai, harus ada nama dan kategori
        name = data_pecah[0].strip()
        category = data_pecah[1].strip()
        try:
            self._execute("INSERT INTO employees (nama, job_name) VALUES (?, ?)", (name, category), commit=True)
            return True
        except sqlite3.IntegrityError:
            return False

    def update_employee(self, employee_id: int, new_name: str) -> bool:
        data_pecah = new_name.split("|")
        if len(data_pecah) < 2:
            return False  # Format tidak sesuai, harus ada nama dan kategori
        new_name = data_pecah[0].strip()
        category = data_pecah[1].strip()
        try:
            self._execute(
                "UPDATE employees SET nama=?, job_name=? WHERE id=?",
                (new_name, category, employee_id),
                commit=True,
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_tasks(self) -> List[Tuple[int, str, float]]:
        cursor = self._execute("SELECT id, task_name, COALESCE(wage, 0) FROM tasks ORDER BY task_name")
        return cursor.fetchall()

    def get_task(self, task_id: int) -> Optional[Tuple[int, str, float]]:
        cursor = self._execute(
            "SELECT id, task_name, COALESCE(wage, 0) FROM tasks WHERE id=?",
            (task_id,),
        )
        row = cursor.fetchone()
        return row if row else None

    def add_task(self, task_name: str, wage: float, description: str = "") -> bool:
        try:
            self._execute(
                "INSERT INTO tasks (task_name, wage, description) VALUES (?, ?, ?)",
                (task_name, wage, description),
                commit=True,
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def update_task(self, task_id: int, task_name: str, wage: float) -> bool:
        try:
            self._execute(
                "UPDATE tasks SET task_name=?, wage=? WHERE id=?",
                (task_name, wage, task_id),
                commit=True,
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def assign_task(self, employee_id: int, task_id: int) -> bool:
        try:
            self._execute(
                "INSERT INTO tasks_employees (employee_id, task_id, qty, waktu) VALUES (?, ?, ?, datetime('now', 'localtime'))",
                (employee_id, task_id, 0),
                commit=True,
            )
            return True
        except sqlite3.IntegrityError:
            return False

    def get_assigned_tasks_for_employee(self, employee_id: int) -> List[Tuple[int, str, float]]:
        cursor = self._execute(
            """
            SELECT t.id, t.task_name, COALESCE(t.wage, 0)
            FROM tasks_employees te
            JOIN tasks t ON t.id = te.task_id
            WHERE te.employee_id=?
            ORDER BY t.task_name
            """,
            (employee_id,),
        )
        return cursor.fetchall()

    def get_week_range(self, anchor_dt: Optional[datetime] = None) -> Tuple[str, str]:
        dt = anchor_dt or datetime.now()
        weekday = dt.weekday()
        # Definisi minggu: Sabtu (start) sampai Kamis (end).
        offset_to_saturday = (weekday - 5) % 7
        week_start = (dt - timedelta(days=offset_to_saturday)).date()
        week_end = week_start + timedelta(days=6)
        return week_start.isoformat(), week_end.isoformat()

    def add_report(self, user_id: str, nama: str, jenis_input: str, detail: str, waktu: str):
        self._execute(
            "INSERT INTO laporan (user_id, nama, jenis_input, detail, waktu) VALUES (?, ?, ?, ?, ?)",
            (user_id, nama, jenis_input, detail, waktu),
            commit=True,
        )

    def add_structured_report(
        self,
        user_id: str,
        employee_id: int,
        task_id: int,
        qty: int,
        wage_per_unit: float,
        jenis_input: str,
        detail: str,
        waktu: str,
        notes: str = "",
    ):
        employee_name = self.get_employee_name(employee_id)
        week_start, week_end = self.get_week_range(datetime.strptime(waktu, "%Y-%m-%d %H:%M:%S"))
        self._execute(
            """
            INSERT INTO laporan (
                user_id, nama, jenis_input, detail, waktu,
                employee_id, task_id, qty, wage_per_unit, week_start, week_end, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                employee_name,
                jenis_input,
                detail,
                waktu,
                employee_id,
                task_id,
                qty,
                wage_per_unit,
                week_start,
                week_end,
                notes,
            ),
            commit=True,
        )

    def get_recent_user_reports(self, user_id: str, limit: int = 5) -> List[Tuple[str, str, str, str]]:
        cursor = self._execute(
            "SELECT nama, jenis_input, detail, waktu FROM laporan WHERE user_id=? ORDER BY id DESC LIMIT ?",
            (user_id, limit),
        )
        return cursor.fetchall()

    def get_recent_reports(self, limit: int = 10) -> List[Tuple[int, str, str]]:
        cursor = self._execute(
            "SELECT id, nama, jenis_input FROM laporan ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()

    def update_report_detail(self, report_id: int, detail: str, waktu: str):
        self._execute(
            "UPDATE laporan SET detail=?, waktu=? WHERE id=?",
            (detail, waktu, report_id),
            commit=True,
        )

    def get_weekly_summary(
        self,
        week_start: str,
        week_end: str,
        employee_id: Optional[int] = None,
    ) -> List[Tuple[str, str, int, float]]:
        params = [week_start, week_end]
        employee_filter_sql = ""
        if employee_id is not None:
            employee_filter_sql = " AND l.employee_id = ?"
            params.append(employee_id)

        cursor = self._execute(
            f"""
            SELECT
                waktu,
                e.nama,
                t.task_name,
                COALESCE(l.qty, 0) AS qty,
                COALESCE(l.qty, 0) * COALESCE(l.wage_per_unit, 0) AS pay
            FROM laporan l
            JOIN employees e ON e.id = l.employee_id
            JOIN tasks t ON t.id = l.task_id
            WHERE l.week_start = ?
              AND l.week_end = ?
              AND l.qty IS NOT NULL
              AND l.wage_per_unit IS NOT NULL
              {employee_filter_sql}
            ORDER BY e.nama, t.task_name
            """,
            tuple(params),
        )
        return cursor.fetchall()

    def get_unstructured_report_count(
        self,
        week_start: str,
        week_end: str,
        employee_id: Optional[int] = None,
    ) -> int:
        params = [week_start, week_end]
        employee_filter_sql = ""
        if employee_id is not None:
            employee_filter_sql = " AND employee_id = ?"
            params.append(employee_id)

        cursor = self._execute(
            f"""
            SELECT COUNT(*)
            FROM laporan
            WHERE date(waktu) BETWEEN ? AND ?
              AND (employee_id IS NULL OR task_id IS NULL OR qty IS NULL OR wage_per_unit IS NULL)
              {employee_filter_sql}
            """,
            tuple(params),
        )
        row = cursor.fetchone()
        return row[0] if row else 0

    def get_weekly_report_count_per_employee(
        self,
        week_start: str,
        week_end: str,
        employee_id: Optional[int] = None,
    ) -> List[Tuple[str, int]]:
        params = [week_start, week_end]
        employee_filter_sql = ""
        if employee_id is not None:
            employee_filter_sql = " AND l.employee_id = ?"
            params.append(employee_id)

        cursor = self._execute(
            f"""
            SELECT e.nama, COUNT(l.id) AS total_laporan
            FROM laporan l
            JOIN employees e ON e.id = l.employee_id
            WHERE l.week_start = ?
              AND l.week_end = ?
              AND l.qty IS NOT NULL
              AND l.wage_per_unit IS NOT NULL
              {employee_filter_sql}
            GROUP BY e.id
            ORDER BY e.nama
            """,
            tuple(params),
        )
        return cursor.fetchall()

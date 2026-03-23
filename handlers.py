import csv
import io
from datetime import datetime, timedelta

from telebot import types

from database import Database


class WorkReportHandlers:
    """Menampung semua handler Telegram agar file utama tetap tipis."""

    def __init__(self, bot, db: Database):
        self.bot = bot
        self.db = db

    def register(self):
        @self.bot.message_handler(commands=["start"])
        def menu_utama(message):
            self._send_main_menu(message.chat.id)

        @self.bot.callback_query_handler(func=lambda call: True)
        def respon_tombol(call: types.CallbackQuery):
            user_id = str(call.from_user.id)
            waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            if call.data in ("menu_jahit", "menu_absen"):
                action = "jahit" if call.data == "menu_jahit" else "absen"
                self._show_employee_picker(call, action)
                return

            if call.data.startswith("pilih_"):
                self._handle_employee_selected(call, user_id, waktu_sekarang)
                return

            if call.data == "menu_edit":
                self._show_edit_menu(call)
                return

            if call.data == "edit_employee":
                self._show_employee_edit_menu(call.message.chat.id)
                return

            if call.data == "add_employee":
                msg = self.bot.send_message(call.message.chat.id, "👤 Masukkan nama karyawan baru: (Format: Nama Lengkap | Kategori)")
                self.bot.register_next_step_handler(msg, self.simpan_karyawan_baru)
                return

            if call.data.startswith("edit_emp_"):
                emp_id = int(call.data.split("_")[2])
                msg = self.bot.send_message(call.message.chat.id, "👤 Masukkan nama baru untuk karyawan: (Format: Nama Lengkap | Kategori)")
                self.bot.register_next_step_handler(msg, self.simpan_edit_karyawan, emp_id)
                return

            if call.data == "edit_tasks":
                self._show_tasks_edit_menu(call.message.chat.id)
                return

            if call.data == "add_task":
                msg = self.bot.send_message(
                    call.message.chat.id,
                    "📋 Masukkan data pekerjaan baru dengan format: Nama Pekerjaan | UpahPerUnit\nContoh: Jahit Kemeja | 5000",
                )
                self.bot.register_next_step_handler(msg, self.simpan_task_baru)
                return

            if call.data.startswith("edit_task_"):
                task_id = int(call.data.split("_")[2])
                msg = self.bot.send_message(
                    call.message.chat.id,
                    "📋 Masukkan data pekerjaan baru dengan format: Nama Pekerjaan | UpahPerUnit\nContoh: Jahit Kemeja | 5000",
                )
                self.bot.register_next_step_handler(msg, self.simpan_edit_task, task_id)
                return

            if call.data == "edit_laporan":
                self._show_report_edit_menu(call.message.chat.id)
                return

            if call.data.startswith("edit_lap_"):
                lap_id = int(call.data.split("_")[2])
                msg = self.bot.send_message(call.message.chat.id, "📝 Masukkan detail laporan baru:")
                self.bot.register_next_step_handler(msg, self.simpan_edit_laporan, lap_id)
                return

            if call.data.startswith("inputtask_"):
                self._handle_input_task(call)
                return

            if call.data == "menu_laporan":
                self._show_user_reports(call.message.chat.id, user_id)
                return

            if call.data == "menu_weekly_report":
                self._show_weekly_scope_options(call.message.chat.id)
                return

            if call.data == "weekly_current":
                week_start, week_end = self.db.get_week_range()
                self._show_weekly_summary(call.message.chat.id, week_start, week_end)
                return

            if call.data == "weekly_previous":
                previous_anchor = datetime.now() - timedelta(days=7)
                week_start, week_end = self.db.get_week_range(previous_anchor)
                self._show_weekly_summary(call.message.chat.id, week_start, week_end)
                return

            if call.data == "weekly_custom":
                msg = self.bot.send_message(
                    call.message.chat.id,
                    "📅 Masukkan tanggal awal minggu (Sabtu) dengan format YYYY-MM-DD.\nContoh: 2026-03-21",
                )
                self.bot.register_next_step_handler(msg, self.simpan_custom_week_start)
                return

            if call.data.startswith("weekly_export_"):
                self._handle_weekly_export(call)
                return

            if call.data == "weekly_scope_all":
                self._show_weekly_options(call.message.chat.id, None)
                return

            if call.data == "weekly_scope_single":
                self._show_weekly_employee_picker(call.message.chat.id)
                return

            if call.data.startswith("weekly_scope_emp_"):
                employee_id = int(call.data.split("_")[3])
                self._show_weekly_options(call.message.chat.id, employee_id)
                return

            if call.data.startswith("weekly_period_"):
                self._handle_weekly_period_selection(call)
                return

            if call.data == "nav_main":
                self._send_main_menu(call.message.chat.id)
                return

            if call.data == "nav_edit":
                self._send_edit_menu(call.message.chat.id)
                return

            if call.data == "nav_weekly_scope":
                self._show_weekly_scope_options(call.message.chat.id)
                return

    def _send_main_menu(self, chat_id: int):
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn1 = types.InlineKeyboardButton("1. Input Pekerjaan (Jahit)", callback_data="menu_jahit")
        btn2 = types.InlineKeyboardButton("2. Input Absen (Di Rumah)", callback_data="menu_absen")
        btn3 = types.InlineKeyboardButton("3. Edit Data", callback_data="menu_edit")
        btn4 = types.InlineKeyboardButton("4. Lihat Laporan", callback_data="menu_laporan")
        btn5 = types.InlineKeyboardButton("5. Laporan Mingguan (Admin)", callback_data="menu_weekly_report")
        markup.add(btn1, btn2, btn3, btn4, btn5)
        self.bot.send_message(
            chat_id,
            "Halo! 👋 Selamat datang di Sistem Pencatatan Kerja.\nSilakan pilih menu di bawah ini:",
            reply_markup=markup,
        )

    def _send_edit_menu(self, chat_id: int):
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_edit_employee = types.InlineKeyboardButton("Edit Data Karyawan", callback_data="edit_employee")
        btn_edit_tasks = types.InlineKeyboardButton("Edit Data Pekerjaan & Upah", callback_data="edit_tasks")
        btn_edit_laporan = types.InlineKeyboardButton("Edit Data Laporan", callback_data="edit_laporan")
        markup.add(btn_edit_employee, btn_edit_tasks, btn_edit_laporan)
        self.bot.send_message(chat_id, "🔧 Pilih data yang ingin Anda edit:", reply_markup=markup)

    def _navigation_markup(self, back_callback: str):
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("⬅️ Kembali", callback_data=back_callback),
            types.InlineKeyboardButton("🏠 Menu Utama", callback_data="nav_main"),
        )
        return markup

    def _show_employee_picker(self, call: types.CallbackQuery, action: str):
        employees = self.db.get_employees()
        if not employees:
            self.bot.send_message(
                call.message.chat.id,
                "⚠️ Belum ada data karyawan. Tambahkan dulu di menu Edit Data.",
            )
            return

        markup = types.InlineKeyboardMarkup(row_width=2)
        for emp_id, nama, job_name in employees:
            markup.add(types.InlineKeyboardButton(f"{nama} ({job_name})", callback_data=f"pilih_{action}_{emp_id}"))
        
        nav = self._navigation_markup("nav_main")
        for row in nav.keyboard:
            markup.row(*row)

        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="👤 Silakan pilih nama Anda:",
            reply_markup=markup,
        )

    def _handle_employee_selected(self, call: types.CallbackQuery, user_id: str, waktu_sekarang: str):
        data_pecah = call.data.split("_", 2)
        if len(data_pecah) < 3:
            self.bot.send_message(call.message.chat.id, "⚠️ Format data tidak valid.")
            return

        action = data_pecah[1]
        employee_id = int(data_pecah[2])
        nama_karyawan = self.db.get_employee_name(employee_id)

        if not nama_karyawan:
            self.bot.send_message(call.message.chat.id, "⚠️ Karyawan tidak ditemukan.")
            return

        if action == "jahit":
            tasks = self.db.get_tasks()

            markup = types.InlineKeyboardMarkup(row_width=1)
            for task_id, task_name, wage in tasks:
                label = f"{task_name} (default upah: {self._format_rupiah(wage)})"
                markup.add(
                    types.InlineKeyboardButton(
                        label,
                        callback_data=f"inputtask_{employee_id}_{task_id}",
                    )
                )
            nav = self._navigation_markup("nav_main")
            for row in nav.keyboard:
                markup.row(*row)
            self.bot.send_message(
                call.message.chat.id,
                f"👤 Nama: {nama_karyawan}\n📌 Pilih pekerjaan yang dikerjakan:",
                reply_markup=markup,
            )
            return

        if action == "absen":
            self.db.add_report(user_id, nama_karyawan, "Absen", "Hadir di rumah", waktu_sekarang)
            self.bot.send_message(
                call.message.chat.id,
                f"✅ Absen berhasil dicatat!\n\n👤 Nama: {nama_karyawan}\n⏰ Waktu: {waktu_sekarang}",
                reply_markup=self._navigation_markup("nav_main"),
            )

    def _show_edit_menu(self, call: types.CallbackQuery):
        markup = types.InlineKeyboardMarkup(row_width=1)
        btn_edit_employee = types.InlineKeyboardButton("Edit Data Karyawan", callback_data="edit_employee")
        btn_edit_tasks = types.InlineKeyboardButton("Edit Data Pekerjaan & Upah", callback_data="edit_tasks")
        btn_edit_laporan = types.InlineKeyboardButton("Edit Data Laporan", callback_data="edit_laporan")
        markup.add(btn_edit_employee, btn_edit_tasks, btn_edit_laporan)
        self.bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🔧 Pilih data yang ingin Anda edit:",
            reply_markup=markup,
        )

    def _show_employee_edit_menu(self, chat_id: int):
        employees = self.db.get_employees()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for emp_id, nama, job_name in employees:
            markup.add(types.InlineKeyboardButton(f"{nama} ({job_name})", callback_data=f"edit_emp_{emp_id}"))
        markup.add(types.InlineKeyboardButton("➕ Tambah Karyawan Baru", callback_data="add_employee"))
        nav = self._navigation_markup("nav_edit")
        for row in nav.keyboard:
            markup.row(*row)
        self.bot.send_message(chat_id, "👥 Pilih karyawan untuk diedit atau tambah baru:", reply_markup=markup)

    def _show_tasks_edit_menu(self, chat_id: int):
        tasks = self.db.get_tasks()
        markup = types.InlineKeyboardMarkup(row_width=1)
        for task_id, task_name, wage in tasks:
            markup.add(
                types.InlineKeyboardButton(
                    f"{task_name} - {self._format_rupiah(wage)}",
                    callback_data=f"edit_task_{task_id}",
                )
            )
        markup.add(types.InlineKeyboardButton("➕ Tambah Pekerjaan Baru", callback_data="add_task"))
        nav = self._navigation_markup("nav_edit")
        for row in nav.keyboard:
            markup.row(*row)
        self.bot.send_message(chat_id, "📋 Pilih pekerjaan untuk diedit atau tambah baru:", reply_markup=markup)

    def _show_report_edit_menu(self, chat_id: int):
        laporan = self.db.get_recent_reports(limit=10)
        markup = types.InlineKeyboardMarkup(row_width=1)
        for report_id, nama, jenis in laporan:
            markup.add(types.InlineKeyboardButton(f"{nama} - {jenis}", callback_data=f"edit_lap_{report_id}"))
        nav = self._navigation_markup("nav_edit")
        for row in nav.keyboard:
            markup.row(*row)
        self.bot.send_message(chat_id, "📄 Pilih laporan untuk diedit:", reply_markup=markup)

    def _handle_input_task(self, call: types.CallbackQuery):
        data_pecah = call.data.split("_", 2)
        if len(data_pecah) < 3:
            self.bot.send_message(call.message.chat.id, "⚠️ Format pekerjaan input tidak valid.")
            return

        employee_id = int(data_pecah[1])
        task_id = int(data_pecah[2])
        employee_name = self.db.get_employee_name(employee_id)
        task_data = self.db.get_task(task_id)
        if not employee_name or not task_data:
            self.bot.send_message(call.message.chat.id, "⚠️ Data karyawan atau pekerjaan tidak ditemukan.")
            return

        _, task_name, default_wage = task_data
        msg = self.bot.send_message(
            call.message.chat.id,
            f"🧵 Pekerjaan: {task_name}\n👤 Karyawan: {employee_name}\n\nMasukkan qty (jumlah unit), contoh: 50",
        )
        self.bot.register_next_step_handler(
            msg,
            self.simpan_qty_jahit,
            employee_id,
            task_id,
            employee_name,
            task_name,
            default_wage,
        )

    def _show_weekly_scope_options(self, chat_id: int):
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(types.InlineKeyboardButton("Semua Karyawan", callback_data="weekly_scope_all"))
        markup.add(types.InlineKeyboardButton("Pilih 1 Karyawan", callback_data="weekly_scope_single"))
        nav = self._navigation_markup("nav_main")
        for row in nav.keyboard:
            markup.row(*row)
        self.bot.send_message(chat_id, "👥 Pilih cakupan laporan mingguan:", reply_markup=markup)

    def _show_weekly_employee_picker(self, chat_id: int):
        employees = self.db.get_employees()
        if not employees:
            self.bot.send_message(chat_id, "⚠️ Belum ada data karyawan.")
            return

        markup = types.InlineKeyboardMarkup(row_width=1)
        for employee_id, nama, job_name in employees:
            markup.add(
                types.InlineKeyboardButton(
                    f"{nama} ({job_name})",
                    callback_data=f"weekly_scope_emp_{employee_id}",
                )
            )
        nav = self._navigation_markup("nav_weekly_scope")
        for row in nav.keyboard:
            markup.row(*row)
        self.bot.send_message(chat_id, "👤 Pilih karyawan yang ingin dilihat:", reply_markup=markup)

    def _show_weekly_options(self, chat_id: int, employee_id: int = None):
        scope_token = "all" if employee_id is None else str(employee_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "Minggu Ini (Sabtu-Kamis)",
                callback_data=f"weekly_period_current_{scope_token}",
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "Minggu Lalu (Sabtu-Kamis)",
                callback_data=f"weekly_period_previous_{scope_token}",
            )
        )
        markup.add(
            types.InlineKeyboardButton(
                "Custom (Input Tanggal Sabtu)",
                callback_data=f"weekly_period_custom_{scope_token}",
            )
        )
        nav = self._navigation_markup("nav_weekly_scope")
        for row in nav.keyboard:
            markup.row(*row)
        self.bot.send_message(chat_id, "📅 Pilih periode laporan mingguan:", reply_markup=markup)

    def _handle_weekly_period_selection(self, call: types.CallbackQuery):
        data_pecah = call.data.split("_", 3)
        if len(data_pecah) < 4:
            self.bot.send_message(call.message.chat.id, "⚠️ Format periode mingguan tidak valid.")
            return

        period_type = data_pecah[2]
        scope_token = data_pecah[3]
        employee_id = None if scope_token == "all" else int(scope_token)

        if period_type == "current":
            week_start, week_end = self.db.get_week_range()
            self._show_weekly_summary(call.message.chat.id, week_start, week_end, employee_id)
            return

        if period_type == "previous":
            previous_anchor = datetime.now() - timedelta(days=7)
            week_start, week_end = self.db.get_week_range(previous_anchor)
            self._show_weekly_summary(call.message.chat.id, week_start, week_end, employee_id)
            return

        if period_type == "custom":
            msg = self.bot.send_message(
                call.message.chat.id,
                "📅 Masukkan tanggal awal minggu (Sabtu) dengan format YYYY-MM-DD.\nContoh: 2026-03-21",
            )
            self.bot.register_next_step_handler(msg, self.simpan_custom_week_start, employee_id)
            return

        self.bot.send_message(call.message.chat.id, "⚠️ Tipe periode tidak dikenali.")

    def _show_weekly_summary(self, chat_id: int, week_start: str, week_end: str, employee_id: int = None):
        rows = self.db.get_weekly_summary(week_start, week_end, employee_id)
        report_counts = dict(self.db.get_weekly_report_count_per_employee(week_start, week_end, employee_id))
        filter_name = self.db.get_employee_name(employee_id) if employee_id is not None else None
        if not rows:
            unstructured_count = self.db.get_unstructured_report_count(week_start, week_end, employee_id)
            if unstructured_count > 0:
                self.bot.send_message(
                    chat_id,
                    "Belum ada data terstruktur untuk periode "
                    f"{self._format_date_id(week_start)} s/d {self._format_date_id(week_end)}.\n"
                    f"Ada {unstructured_count} laporan lama belum terstruktur.",
                    reply_markup=self._navigation_markup("nav_weekly_scope"),
                )
                return
            self.bot.send_message(
                chat_id,
                f"Belum ada data terstruktur untuk periode {self._format_date_id(week_start)} s/d {self._format_date_id(week_end)}.",
                reply_markup=self._navigation_markup("nav_weekly_scope"),
            )
            return

        result_per_employee = {}
        grand_total = 0.0
        for waktu, employee_name, task_name, total_qty, total_pay in rows:
            if employee_name not in result_per_employee:
                result_per_employee[employee_name] = {"lines": [], "total": 0.0}
            result_per_employee[employee_name]["lines"].append((waktu, task_name, total_qty, total_pay))
            result_per_employee[employee_name]["total"] += float(total_pay)
            grand_total += float(total_pay)

        lines = [
            "📊 Rekap Mingguan Karyawan",
            f"Periode: {self._format_date_id(week_start)} s/d {self._format_date_id(week_end)} (Sabtu-Kamis)",
            f"Filter: {filter_name if filter_name else 'Semua karyawan'}",
            "",
        ]

        for employee_name, payload in result_per_employee.items():
            lines.append(f"👤 {employee_name}")
            lines.append(f"Total laporan: {report_counts.get(employee_name, 0)}")
            for waktu, task_name, total_qty, total_pay in payload["lines"]:
                lines.append(
                    f"- {self._format_datetime_id(waktu)} | {task_name}: {int(total_qty)} unit | Estimasi {self._format_rupiah(total_pay)}"
                )
            lines.append(f"Subtotal: {self._format_rupiah(payload['total'])}")
            lines.append("")

        lines.append(f"💰 Grand Total: {self._format_rupiah(grand_total)}")
        unstructured_count = self.db.get_unstructured_report_count(week_start, week_end, employee_id)
        if unstructured_count > 0:
            lines.append(f"⚠️ Catatan: {unstructured_count} laporan lama belum terstruktur dan tidak ikut kalkulasi.")

        self._send_long_message(chat_id, "\n".join(lines))
        self._send_weekly_export_button(chat_id, week_start, week_end, employee_id)

    def _send_weekly_export_button(self, chat_id: int, week_start: str, week_end: str, employee_id: int = None):
        packed_start = week_start.replace("-", "")
        packed_end = week_end.replace("-", "")
        scope_token = "all" if employee_id is None else str(employee_id)
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "⬇️ Export CSV Periode Ini",
                callback_data=f"weekly_export_{packed_start}_{packed_end}_{scope_token}",
            )
        )
        nav = self._navigation_markup("nav_weekly_scope")
        for row in nav.keyboard:
            markup.row(*row)
        self.bot.send_message(chat_id, "Ingin unduh rekap periode ini?", reply_markup=markup)

    def _handle_weekly_export(self, call: types.CallbackQuery):
        data_pecah = call.data.split("_", 4)
        if len(data_pecah) < 5:
            self.bot.send_message(call.message.chat.id, "⚠️ Format export mingguan tidak valid.")
            return

        packed_start = data_pecah[2]
        packed_end = data_pecah[3]
        scope_token = data_pecah[4]
        employee_id = None if scope_token == "all" else int(scope_token)
        if len(packed_start) != 8 or len(packed_end) != 8:
            self.bot.send_message(call.message.chat.id, "⚠️ Format periode export tidak valid.")
            return

        week_start = f"{packed_start[:4]}-{packed_start[4:6]}-{packed_start[6:8]}"
        week_end = f"{packed_end[:4]}-{packed_end[4:6]}-{packed_end[6:8]}"

        rows = self.db.get_weekly_summary(week_start, week_end, employee_id)
        report_counts = dict(self.db.get_weekly_report_count_per_employee(week_start, week_end, employee_id))
        if not rows:
            self.bot.send_message(
                call.message.chat.id,
                f"Tidak ada data terstruktur untuk diexport pada periode {week_start} s/d {week_end}.",
                reply_markup=self._navigation_markup("nav_weekly_scope"),
            )
            return

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "periode_start",
                "periode_end",
                "employee",
                "task",
                "total_qty",
                "estimated_pay",
                "total_laporan_employee",
            ]
        )
        for employee_name, task_name, total_qty, total_pay in rows:
            writer.writerow(
                [
                    week_start,
                    week_end,
                    employee_name,
                    task_name,
                    int(total_qty),
                    float(total_pay),
                    report_counts.get(employee_name, 0),
                ]
            )

        writer.writerow([])
        writer.writerow(["employee", "total_laporan"])
        for employee_name, total_laporan in sorted(report_counts.items()):
            writer.writerow([employee_name, total_laporan])

        unstructured_count = self.db.get_unstructured_report_count(week_start, week_end, employee_id)
        writer.writerow([])
        writer.writerow(["notes", f"unstructured_reports_excluded={unstructured_count}"])

        csv_bytes = io.BytesIO(output.getvalue().encode("utf-8"))
        file_suffix = "all" if employee_id is None else f"emp_{employee_id}"
        csv_bytes.name = f"weekly_report_{packed_start}_{packed_end}_{file_suffix}.csv"
        csv_bytes.seek(0)
        self.bot.send_document(
            call.message.chat.id,
            csv_bytes,
            caption=f"📁 Export rekap mingguan {week_start} s/d {week_end}",
        )
        self.bot.send_message(
            call.message.chat.id,
            "Pilih aksi berikutnya:",
            reply_markup=self._navigation_markup("nav_weekly_scope"),
        )

    def simpan_custom_week_start(self, message, employee_id: int = None):
        raw_date = message.text.strip()
        try:
            week_start_dt = datetime.strptime(raw_date, "%Y-%m-%d")
        except ValueError:
            self.bot.reply_to(message, "⚠️ Format tanggal tidak valid. Gunakan YYYY-MM-DD.", reply_markup=self._navigation_markup("nav_weekly_scope"))
            return

        if week_start_dt.weekday() != 5:
            self.bot.reply_to(
                message,
                "⚠️ Tanggal awal harus hari Sabtu.",
                reply_markup=self._navigation_markup("nav_weekly_scope"),
            )
            return

        week_end_dt = week_start_dt + timedelta(days=6)
        self._show_weekly_summary(
            message.chat.id,
            week_start_dt.strftime("%Y-%m-%d"),
            week_end_dt.strftime("%Y-%m-%d"),
            employee_id,
        )

    def _send_long_message(self, chat_id: int, text: str, chunk_size: int = 3500):
        start = 0
        while start < len(text):
            chunk = text[start : start + chunk_size]
            self.bot.send_message(chat_id, chunk)
            start += chunk_size

    def _format_rupiah(self, value: float) -> str:
        amount = int(round(float(value)))
        return f"Rp{amount:,}".replace(",", ".")

    def _format_date_id(self, date_str: str) -> str:
        """Format tanggal menjadi: Hari, Tanggal Bulan Tahun (Sabtu, 21 Maret 2026)"""
        bulan_indo = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        hari_indo = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        nama_hari = hari_indo[dt.weekday()]
        nama_bulan = bulan_indo[dt.month - 1]
        return f"{nama_hari}, {dt.day} {nama_bulan} {dt.year}"

    def _format_datetime_id(self, datetime_str: str) -> str:
        """Format datetime menjadi: Hari, Tanggal Bulan Tahun Jam:Menit"""
        bulan_indo = [
            "Januari", "Februari", "Maret", "April", "Mei", "Juni",
            "Juli", "Agustus", "September", "Oktober", "November", "Desember"
        ]
        hari_indo = ["Senin", "Selasa", "Rabu", "Kamis", "Jumat", "Sabtu", "Minggu"]
        
        dt = datetime.strptime(datetime_str, "%Y-%m-%d %H:%M:%S")
        nama_hari = hari_indo[dt.weekday()]
        nama_bulan = bulan_indo[dt.month - 1]
        return f"{nama_hari}, {dt.day} {nama_bulan} {dt.year}"

    def _show_user_reports(self, chat_id: int, user_id: str):
        data_laporan = self.db.get_recent_user_reports(user_id, limit=5)
        if not data_laporan:
            self.bot.send_message(
                chat_id,
                "Belum ada laporan yang tercatat dari akun Telegram ini.",
                reply_markup=self._navigation_markup("nav_main"),
            )
            return

        teks_laporan = "📊 **5 Laporan Terakhir Anda:**\n\n"
        for nama, jenis_input, detail, waktu in data_laporan:
            teks_laporan += f"👤 {nama}\n🔹 {jenis_input}\n📝 {detail}\n⏰ {waktu}\n\n"
        self.bot.send_message(
            chat_id,
            teks_laporan,
            parse_mode="Markdown",
            reply_markup=self._navigation_markup("nav_main"),
        )

    def simpan_karyawan_baru(self, message):
        new_name = message.text.strip()
        if not new_name:
            self.bot.reply_to(message, "⚠️ Nama tidak boleh kosong.")
            return

        if not self.db.add_employee(new_name):
            self.bot.reply_to(
                message,
                f"⚠️ Nama '{new_name}' sudah terdaftar. Silakan coba nama lain.",
                reply_markup=self._navigation_markup("nav_edit"),
            )
            return

        self.bot.reply_to(
            message,
            f"✅ Karyawan '{new_name}' berhasil ditambahkan!",
            reply_markup=self._navigation_markup("nav_edit"),
        )

    def simpan_task_baru(self, message):
        task_name, wage = self._parse_task_input(message.text)
        if not task_name:
            self.bot.reply_to(
                message,
                "⚠️ Format tidak valid. Gunakan: Nama Pekerjaan | UpahPerUnit",
                reply_markup=self._navigation_markup("nav_edit"),
            )
            return

        if self.db.add_task(task_name, wage):
            self.bot.reply_to(
                message,
                f"✅ Pekerjaan '{task_name}' berhasil ditambahkan dengan upah {self._format_rupiah(wage)}!",
                reply_markup=self._navigation_markup("nav_edit"),
            )
            return

        self.bot.reply_to(
            message,
            f"⚠️ Pekerjaan '{task_name}' sudah terdaftar. Silakan coba nama lain.",
            reply_markup=self._navigation_markup("nav_edit"),
        )

    def simpan_edit_karyawan(self, message, emp_id: int):
        nama_baru = message.text.strip()
        if not nama_baru:
            self.bot.reply_to(
                message,
                "⚠️ Nama karyawan tidak boleh kosong.",
                reply_markup=self._navigation_markup("nav_edit"),
            )
            return

        if self.db.update_employee(emp_id, nama_baru):
            self.bot.reply_to(message, f"✅ Nama karyawan berhasil diubah menjadi '{nama_baru}'!", reply_markup=self._navigation_markup("nav_edit"))
            return

        self.bot.reply_to(
            message,
            f"⚠️ Nama '{nama_baru}' sudah terdaftar. Silakan coba nama lain.",
            reply_markup=self._navigation_markup("nav_edit"),
        )

    def simpan_edit_task(self, message, task_id: int):
        task_name, wage = self._parse_task_input(message.text)
        if not task_name:
            self.bot.reply_to(
                message,
                "⚠️ Format tidak valid. Gunakan: Nama Pekerjaan | UpahPerUnit",
                reply_markup=self._navigation_markup("nav_edit"),
            )
            return

        if self.db.update_task(task_id, task_name, wage):
            self.bot.reply_to(
                message,
                f"✅ Pekerjaan berhasil diubah menjadi '{task_name}' dengan upah {self._format_rupiah(wage)}!",
                reply_markup=self._navigation_markup("nav_edit"),
            )
            return

        self.bot.reply_to(
            message,
            f"⚠️ Pekerjaan '{task_name}' sudah terdaftar. Silakan coba nama lain.",
            reply_markup=self._navigation_markup("nav_edit"),
        )

    def simpan_qty_jahit(
        self,
        message,
        employee_id: int,
        task_id: int,
        employee_name: str,
        task_name: str,
        default_wage: float,
    ):
        raw_qty = message.text.strip()
        if not raw_qty.isdigit() or int(raw_qty) <= 0:
            self.bot.reply_to(
                message,
                "⚠️ Qty harus angka bulat positif. Coba lagi dari awal input jahit.",
                reply_markup=self._navigation_markup("nav_main"),
            )
            return

        qty = int(raw_qty)
        msg = self.bot.send_message(
            message.chat.id,
            f"💵 Upah default pekerjaan ini: {self._format_rupiah(default_wage)} per unit.\n"
            "Ketik upah baru atau kirim '' / '-' untuk pakai default.",
        )
        self.bot.register_next_step_handler(
            msg,
            self.simpan_laporan_jahit_terstruktur,
            employee_id,
            task_id,
            employee_name,
            task_name,
            qty,
            default_wage,
        )

    def simpan_laporan_jahit_terstruktur(
        self,
        message,
        employee_id: int,
        task_id: int,
        employee_name: str,
        task_name: str,
        qty: int,
        default_wage: float,
    ):
        raw_wage = message.text.strip()
        if raw_wage in ("", "-"):
            wage_per_unit = float(default_wage)
        else:
            try:
                wage_per_unit = float(raw_wage)
            except ValueError:
                self.bot.reply_to(
                    message,
                    "⚠️ Upah harus angka. Coba lagi dari awal input jahit.",
                    reply_markup=self._navigation_markup("nav_main"),
                )
                return
            if wage_per_unit < 0:
                self.bot.reply_to(
                    message,
                    "⚠️ Upah tidak boleh negatif.",
                    reply_markup=self._navigation_markup("nav_main"),
                )
                return

        user_id = str(message.from_user.id)
        waktu_sekarang = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total_estimasi = qty * wage_per_unit
        detail = (
            f"Pekerjaan: {task_name}, Qty: {qty}, Upah/unit: {self._format_rupiah(wage_per_unit)}, "
            f"Estimasi: {self._format_rupiah(total_estimasi)}"
        )

        self.db.add_structured_report(
            user_id=user_id,
            employee_id=employee_id,
            task_id=task_id,
            qty=qty,
            wage_per_unit=wage_per_unit,
            jenis_input="Jahit Bawa Pulang",
            detail=detail,
            waktu=waktu_sekarang,
        )
        self.bot.reply_to(
            message,
            "✅ Laporan jahit berhasil disimpan!\n\n"
            f"👤 Nama: {employee_name}\n"
            f"🧵 Pekerjaan: {task_name}\n"
            f"🔢 Qty: {qty}\n"
            f"💵 Upah/unit: {self._format_rupiah(wage_per_unit)}\n"
            f"💰 Estimasi bayar: {self._format_rupiah(total_estimasi)}",
            reply_markup=self._navigation_markup("nav_main"),
        )

    def _parse_task_input(self, raw_text: str):
        # Format tunggal ini menjaga parsing tetap sederhana dan konsisten.
        if "|" not in raw_text:
            return None, None
        task_name, raw_wage = [part.strip() for part in raw_text.split("|", 1)]
        if not task_name:
            return None, None
        try:
            wage = float(raw_wage)
        except ValueError:
            return None, None
        if wage < 0:
            return None, None
        return task_name, wage

    def simpan_edit_laporan(self, message, lap_id: int):
        detail_baru = message.text.strip()
        if not detail_baru:
            self.bot.reply_to(
                message,
                "⚠️ Detail laporan tidak boleh kosong.",
                reply_markup=self._navigation_markup("nav_edit"),
            )
            return

        waktu_baru = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.db.update_report_detail(lap_id, detail_baru, waktu_baru)
        self.bot.reply_to(
            message,
            "✅ Laporan berhasil diperbarui.",
            reply_markup=self._navigation_markup("nav_edit"),
        )

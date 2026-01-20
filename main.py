"""
main.py - ממשק משתמש סופי (גריד קבוע 12 כרטיסיות, ללא גלילה)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from listener import FacebookListener
from database import PostDatabase
from analytics import Analytics
import threading
from datetime import datetime
import os
import time
import webbrowser
import re

# --- הגדרות צבעים ועיצוב ---
COLORS = {
    'primary': '#2c3e50',    # כחול כהה (כותרות)
    'secondary': '#34495e',  # כחול אפרפר
    'accent': '#3498db',     # תכלת (כפתורים)
    'success': '#27ae60',    # ירוק
    'danger': '#e74c3c',     # אדום
    'warning': '#f39c12',    # כתום
    'bg': '#ecf0f1',         # רקע כללי בהיר
    'card': '#ffffff',       # רקע כרטיסים (לבן)
    'text': '#2c3e50',       # צבע טקסט ראשי
    'text_light': '#7f8c8d', # צבע טקסט משני
    'sub_text': '#95a5a6'    # צבע טקסט קטן
}

class GuardianGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Facebook Guardian Pro")
        self.root.geometry("1400x950")
        self.root.configure(bg=COLORS['bg'])

        self.listener = FacebookListener()
        self.listener.set_status_callback(self.log_status)
        # חיבור הצינור לכרטיסיות:
        self.listener.set_new_post_callback(self.on_new_post_found)

        self.db = PostDatabase()
        self.analytics = Analytics()
        self.session_start_time = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # בניית הממשק
        self._create_header()
        self._create_dashboard()
        self._create_controls()

        # יצירת אזור הכרטיסיות (ללא גלילה)
        self._create_recent_cards_area()

        # הצגה ראשונית של כרטיסיות עיר-שכונה
        self._create_city_neighborhood_cards()

        self._start_stats_updater()

    def on_closing(self):
        if self.listener.is_listening:
            if not messagebox.askyesno("יציאה", "ההאזנה פעילה. האם לעצור ולצאת?"):
                return
        self.log_status("מבצע יציאה מסודרת...", "WARNING")
        self.listener.force_cleanup()
        self.root.destroy()

    def _create_header(self):
        header = tk.Frame(self.root, bg=COLORS['primary'], height=85)
        header.pack(fill='x')

        inner_header = tk.Frame(header, bg=COLORS['primary'])
        inner_header.pack(fill='x', padx=25, pady=10)

        tk.Label(inner_header, text="🏠", font=('Segoe UI', 35), bg=COLORS['primary'], fg='white').pack(side='right', padx=(0, 15))

        title_frame = tk.Frame(inner_header, bg=COLORS['primary'])
        title_frame.pack(side='right', fill='y')

        # שים לב ל- anchor='e' בסוף השורה - זה מה שמצמיד לימין
        tk.Label(title_frame, text="Facebook Guardian", font=('Segoe UI', 24, 'bold'), bg=COLORS['primary'],
                 fg='white').pack(anchor='e')

        # גם כאן - anchor='e'
        tk.Label(title_frame, text="מערכת ניטור נדל\"ן בזמן אמת", font=('Segoe UI', 11), bg=COLORS['primary'],
                 fg='#bdc3c7').pack(anchor='e', pady=(0, 0))

    # ==============================================================================
    # עיצוב הכרטיסייה
    # ==============================================================================
    def _create_listing_card_widget(self, parent_frame, location, price, rooms, time_str):
        """מייצרת וידג'ט מעוצב של כרטיסייה בודדת"""

        # כרטיס עם מסגרת עדינה
        card_frame = tk.Frame(parent_frame, bg=COLORS['card'], bd=0,
                              highlightthickness=1, highlightbackground="#d0d0d0")

        # פס צבע עליון
        tk.Frame(card_frame, bg=COLORS['accent'], height=4).pack(fill='x')

        # 1. הקטנת רווח עליון (pady) מ-10 ל-5
        content = tk.Frame(card_frame, bg=COLORS['card'], padx=12, pady=5)
        content.pack(fill='both', expand=True)

        # שורה 1: מיקום
        tk.Label(content, text=location, font=('Segoe UI', 11, 'bold'),
                 bg=COLORS['card'], fg=COLORS['primary'], anchor='e').pack(fill='x')

        # שורה 2: מחיר
        price_color = COLORS['success'] if "₪" in str(price) else COLORS['text_light']
        # 2. הקטנת רווחים סביב המחיר ל-(2, 5)
        tk.Label(content, text=price, font=('Segoe UI', 18, 'bold'),
                 bg=COLORS['card'], fg=price_color).pack(pady=(2, 5))

        # שורה 3: פרטים (חדרים + שעה)
        # 3. הצמדה לתחתית (side='bottom')
        bottom_row = tk.Frame(content, bg='#f0f2f5', padx=8, pady=4)
        bottom_row.pack(side='bottom', fill='x', pady=(0, 5))

        # חדרים מימין
        tk.Label(bottom_row, text=f"🛏️ {rooms}", font=('Segoe UI', 9),
                 bg='#f0f2f5', fg='#333').pack(side='right')

        # שעה משמאל
        tk.Label(bottom_row, text=time_str, font=('Segoe UI', 8),
                 bg='#f0f2f5', fg='#888').pack(side='left')

        # 4. === התיקון הקריטי: הגדלת הגובה מ-130 ל-145 ===
        card_frame.pack_propagate(False)
        card_frame.config(width=240, height=145)

        return card_frame

    def _create_dashboard(self):
        dashboard = tk.Frame(self.root, bg=COLORS['bg'])
        dashboard.pack(fill='x', padx=15, pady=20)

        self.card_status = self._create_card(dashboard, "סטטוס", "ממתין", "לא פעיל")
        self.card_status.pack(side='right', fill='both', expand=True, padx=5)

        self.card_time = self._create_card(dashboard, "זמן פעילות", "00:00", "סשן נוכחי")
        self.card_time.pack(side='right', fill='both', expand=True, padx=5)

        self.card_checks = self._create_card(dashboard, "בדיקות היום", "0", "הבאה: --:--")
        self.card_checks.pack(side='right', fill='both', expand=True, padx=5)

        self.card_apartments = self._create_card(dashboard, "דירות היום", "0", "שבוע: 0")
        self.card_apartments.pack(side='right', fill='both', expand=True, padx=5)

        self.card_trends = self._create_card(dashboard, "מחיר ממוצע", "--", "עיר מובילה: --")
        self.card_trends.pack(side='right', fill='both', expand=True, padx=5)

    def _create_card(self, parent, title, value, sub_text=""):
        card = tk.Frame(parent, bg=COLORS['card'], bd=1, relief='flat')
        tk.Frame(card, bg=COLORS['accent'], height=4).pack(fill='x')
        content = tk.Frame(card, bg=COLORS['card'], padx=10, pady=10)
        content.pack(fill='both', expand=True)

        tk.Label(content, text=title, font=('Segoe UI', 10), fg=COLORS['text_light'], bg=COLORS['card']).pack(anchor='e')
        lbl_value = tk.Label(content, text=value, font=('Segoe UI', 22, 'bold'), fg=COLORS['text'], bg=COLORS['card'])
        lbl_value.pack(anchor='e', pady=(2, 0))
        lbl_sub = tk.Label(content, text=sub_text, font=('Segoe UI', 9), fg=COLORS['sub_text'], bg=COLORS['card'])
        lbl_sub.pack(anchor='e', pady=(0, 2))

        card.value_label = lbl_value
        card.sub_label = lbl_sub
        return card

    def _create_controls(self):
        controls = tk.Frame(self.root, bg=COLORS['bg'])
        controls.pack(fill='x', padx=15, pady=(0, 15))

        self.btn_start = tk.Button(controls, text="▶ התחל האזנה", font=('Segoe UI', 12, 'bold'),
                                 bg=COLORS['success'], fg='white', relief='flat', cursor='hand2',
                                 command=self.start_listening, height=2)
        self.btn_start.pack(side='right', fill='x', expand=True, padx=5)

        self.btn_stop = tk.Button(controls, text="⏹ עצור", font=('Segoe UI', 12, 'bold'),
                                bg=COLORS['danger'], fg='white', relief='flat', cursor='hand2',
                                command=self.stop_listening, height=2, state='disabled')
        self.btn_stop.pack(side='right', fill='x', expand=True, padx=5)

        btn_style = {'font': ('Segoe UI', 11), 'bg': COLORS['secondary'], 'fg': 'white', 'relief': 'flat', 'height': 2, 'cursor': 'hand2'}

        tk.Button(controls, text="📋 טבלה", command=self.show_apartments, **btn_style).pack(side='right', fill='x', expand=True, padx=5)
        tk.Button(controls, text="💾 CSV", command=self.export_csv, **btn_style).pack(side='right', fill='x', expand=True, padx=5)
        tk.Button(controls, text="👥 קבוצות", command=self.manage_groups_placeholder, **btn_style).pack(side='right', fill='x', expand=True, padx=5)
        tk.Button(controls, text="⚙️ הגדרות", command=self.open_settings, **btn_style).pack(side='right', fill='x', expand=True, padx=5)

    # ==============================================================================
    # אזור הכרטיסיות (ללא גלילה!)
    # ==============================================================================
    def _create_recent_cards_area(self):
        """יוצר אזור כרטיסיות קבוע"""

        # === 1. מיכל לפס + כרטיסיות ===
        container = tk.Frame(self.root, bg=COLORS['bg'])

        # 🛠️ התיקון כאן: שינינו את padx מ-15 ל-20
        # זה מתקזז עם ה-padx הפנימי של הכרטיסיות העליונות ויוצר יישור מושלם
        container.pack(fill='both', expand=True, padx=20, pady=(4, 20))

        # === 2. הפס הכחול (בתוך container) ===
        header_frame = tk.Frame(container, bg=COLORS['secondary'], pady=7)
        header_frame.pack(fill='x', pady=(0, 5))

        tk.Label(header_frame, text="🗺️ מפת דירות",
                 font=('Segoe UI', 16, 'bold'),
                 bg=COLORS['secondary'], fg='white').pack(side='right', padx=10)

        # כפתור רענון
        refresh_btn = tk.Button(header_frame, text="🔄 רענן", font=('Segoe UI', 10),
                               bg=COLORS['accent'], fg='white', bd=0,
                               padx=15, pady=5, cursor='hand2',
                               command=self._create_city_neighborhood_cards)
        refresh_btn.pack(side='left', padx=10)

        # === 3. אזור הכרטיסיות ===
        # שינוי קטן: הוספתי קצת padding פנימי כדי שהכרטיסיות לא "יידבקו" לפס הכחול
        self.cards_container = tk.Frame(container, bg=COLORS['bg'])
        self.cards_container.pack(fill='both', expand=True)

        # רשימה לשמירת המידע
        self.cards_data_list = []

    # ==============================================================================
    # ניהול נתונים וגריד
    # ==============================================================================
    def add_new_listing_card(self, location, price, rooms):
        """מוסיף נתונים ומצייר מחדש את הגריד"""
        current_time = datetime.now().strftime("%H:%M")

        # 1. יצירת האובייקט החדש
        card_data = {
            'location': location,
            'price': price,
            'rooms': rooms,
            'time': current_time
        }

        # 2. הוספה לראש הרשימה (הכי חדש בהתחלה)
        self.cards_data_list.insert(0, card_data)

        # 3. שמירה על מקסימום 15 כרטיסיות בדיוק
        if len(self.cards_data_list) > 15:
            self.cards_data_list = self.cards_data_list[:15]

        # 4. ציור מחדש
        self._render_cards_grid()

    def _render_cards_grid(self):
        """מוחק את כל הכרטיסיות ומצייר אותן מחדש בסדר הנכון"""
        # ניקוי הוידג'טים הקיימים
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        COLUMNS = 5  # 5 כרטיסיות בשורה

        for index, data in enumerate(self.cards_data_list):
            # חישוב מיקום (שורה ועמודה)
            row = index // COLUMNS
            # הטריק לסידור מימין לשמאל:
            col = COLUMNS - 1 - (index % COLUMNS)

            # יצירת הכרטיס
            card = self._create_listing_card_widget(
                self.cards_container,
                data['location'],
                data['price'],
                data['rooms'],
                data['time']
            )

            # הצבה בגריד עם רווחים
            card.grid(row=row, column=col, padx=10, pady=10)

    # ==============================================================================
    # כרטיסיות עיר-שכונה (חדש!)
    # ==============================================================================
    def _create_city_neighborhood_cards(self):
        """מציג כרטיסיות עיר-שכונה במקום דירות אחרונות"""
        # ניקוי הקונטיינר
        for widget in self.cards_container.winfo_children():
            widget.destroy()

        # שליפת הנתונים
        stats = self.analytics.get_city_neighborhood_stats(min_apartments=3)

        if not stats:
            # אין נתונים - הצג הודעה
            tk.Label(self.cards_container,
                    text="אין מספיק נתונים להצגה (נדרשות לפחות 3 דירות)",
                    font=('Segoe UI', 12),
                    bg=COLORS['bg'],
                    fg=COLORS['text_light']).pack(pady=50)
            return

        # יצירת כרטיסייה לכל עיר
        row = 0
        col = 0
        MAX_COLS = 2  # 2 ערים בשורה

        for city, neighborhoods in stats.items():
            # כרטיסייה של עיר
            city_card = tk.Frame(self.cards_container, bg=COLORS['card'], bd=0,
                                highlightthickness=2, highlightbackground=COLORS['secondary'])
            city_card.grid(row=row, column=col, padx=15, pady=15, sticky='nsew')

            # כותרת העיר
            city_header = tk.Frame(city_card, bg=COLORS['secondary'], pady=8)
            city_header.pack(fill='x')

            total = sum(neighborhoods.values())
            tk.Label(city_header, text=f"🏙️ {city}",
                    font=('Segoe UI', 14, 'bold'),
                    bg=COLORS['secondary'], fg='white').pack(side='right', padx=10)

            tk.Label(city_header, text=f"{total} דירות",
                    font=('Segoe UI', 10),
                    bg=COLORS['secondary'], fg='#bdc3c7').pack(side='left', padx=10)

            # קונטיינר לשכונות
            neighborhoods_container = tk.Frame(city_card, bg=COLORS['card'], padx=10, pady=10)
            neighborhoods_container.pack(fill='both', expand=True)

            # חישוב grid לשכונות
            num_neighborhoods = len(neighborhoods)
            if num_neighborhoods <= 4:
                grid_cols = 2
            elif num_neighborhoods <= 6:
                grid_cols = 3
            else:
                grid_cols = 3  # מקסימום 3 עמודות

            # יצירת כרטיסיות שכונות
            for idx, (neighborhood, count) in enumerate(neighborhoods.items()):
                n_row = idx // grid_cols
                n_col = grid_cols - 1 - (idx % grid_cols)  # RTL

                # כרטיסייה של שכונה
                neigh_card = tk.Frame(neighborhoods_container, bg='white', bd=1,
                                     relief='solid', highlightthickness=1,
                                     highlightbackground='#e0e0e0')
                neigh_card.grid(row=n_row, column=n_col, padx=5, pady=5, sticky='nsew')

                # פס צבע (לפי כמות)
                if count >= 7:
                    bar_color = '#e74c3c'  # אדום - חם!
                elif count >= 5:
                    bar_color = '#9b59b6'  # סגול
                elif count >= 3:
                    bar_color = '#3498db'  # כחול
                else:
                    bar_color = '#2ecc71'  # ירוק

                tk.Frame(neigh_card, bg=bar_color, height=3).pack(fill='x')

                # תוכן השכונה
                content = tk.Frame(neigh_card, bg='white', padx=10, pady=8)
                content.pack(fill='both', expand=True)

                tk.Label(content, text=neighborhood,
                        font=('Segoe UI', 11, 'bold'),
                        bg='white', fg=COLORS['primary']).pack()

                # סה"כ דירות
                count_label = f"{count} דירות" if count > 1 else "דירה 1"
                tk.Label(content, text=count_label,
                        font=('Segoe UI', 13, 'bold'),
                        bg='white', fg=bar_color).pack(pady=3)

            # מעבר לעמודה/שורה הבאה
            col += 1
            if col >= MAX_COLS:
                col = 0
                row += 1

        # הגדרת משקולות לעמודות (כדי שיתפסו שטח שווה)
        for c in range(MAX_COLS):
            self.cards_container.grid_columnconfigure(c, weight=1)

    # ==============================================================================
    # קבלת נתונים מה-Listener
    # ==============================================================================
    def on_new_post_found(self, post_data):
        """מקבל נתונים ומכין אותם לתצוגה"""

        # 1. טיפול במחיר - אחיד עם פסיקים
        price = "לא צוין"
        if post_data.get('price'):
            try:
                # הסר תווים מיותרים והמר למספר
                clean_num = int(str(post_data['price']).replace(',', '').replace('₪', '').strip())
                # פורמט אחיד: ₪ בהתחלה + פסיקים
                price = f"₪{clean_num:,}"
            except (ValueError, TypeError):
                price = "לא צוין"

        # גיבוי: חילוץ מהטקסט
        if price == "לא צוין":
            content = post_data.get('content', '')
            match = re.search(r'(\d{1,3}(?:,\d{3})*)', content)
            if match:
                try:
                    num = int(match.group(1).replace(',', ''))
                    if num > 1000:
                        price = f"₪{num:,}"
                except (ValueError, TypeError):
                    pass

        # 2. מיקום מלא (עיר + שכונה/רחוב)
        # המידע כבר מגיע מה-listener (enriched_data)
        city = post_data.get('city', '')
        loc = post_data.get('location', '')

        if city and loc:
            location = f"{city}, {loc}"
        elif city:
            location = city
        elif loc:
            location = loc
        else:
            location = "לא צוין"

        # קיצור טקסט ארוך
        if len(location) > 25:
            location = location[:23] + "..."

        # 3. חדרים
        rooms = post_data.get('rooms')
        if not rooms:
            rooms = "-"

        display_rooms = str(rooms) if "חד" in str(rooms) else f"{rooms} חד'"

        # רענון כרטיסיות עיר-שכונה (במקום כרטיסייה בודדת)
        self.root.after(0, lambda: self._create_city_neighborhood_cards())

    def log_status(self, message, level='INFO'):
        """לוג לקונסול בלבד"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        clean_msg = re.sub(r'^\[.*?\]\s*', '', str(message))
        print(f"[{timestamp}] [{level}] {clean_msg}")

    def manage_groups_placeholder(self):
        """פותח חלון ניהול קבוצות"""
        from groups_dialog import GroupsDialog
        read_only = self.listener.is_listening
        GroupsDialog(self.root, read_only=read_only)

    def open_settings(self):
        """פותח חלון הגדרות"""
        from settings_dialog import SettingsDialog
        SettingsDialog(self.root)

    def start_listening(self):
        if self.listener.is_listening: return
        self.btn_start.config(state='disabled', bg='#bdc3c7')
        self.btn_stop.config(state='normal', bg=COLORS['danger'])
        self.card_status.value_label.config(text="מפעיל...", fg=COLORS['warning'])
        self.card_status.sub_label.config(text="מתחבר...")
        self.log_status("מאתחל מנוע האזנה...", "INFO")
        self.session_start_time = time.time()

        def run():
            success = self.listener.start_listening()
            if success:
                self.card_status.value_label.config(text="פעיל", fg=COLORS['success'])
                self.card_status.sub_label.config(text="סורק קבוצות")
                self.log_status("המערכת מחוברת ומאזינה בהצלחה", "SUCCESS")
            else:
                self.reset_ui_state()
                self.log_status("נכשל בהפעלה - בדוק חיבור אינטרנט או דפדפן", "ERROR")
        threading.Thread(target=run, daemon=True).start()

    def stop_listening(self):
        self.card_status.value_label.config(text="עוצר...", fg=COLORS['warning'])
        self.btn_stop.config(state='disabled')
        self.log_status("התקבלה פקודת עצירה - סוגר דפדפן...", "WARNING")
        def run():
            self.listener.stop_listening()
            self.reset_ui_state()
            self.log_status("הדפדפן נסגר וההאזנה הופסקה.", "INFO")
        threading.Thread(target=run, daemon=True).start()

    def reset_ui_state(self):
        self.btn_start.config(state='normal', bg=COLORS['success'])
        self.btn_stop.config(state='disabled', bg=COLORS['danger'])
        self.card_status.value_label.config(text="ממתין", fg=COLORS['text_light'])
        self.card_status.sub_label.config(text="לא פעיל")
        self.session_start_time = None
        self.card_checks.value_label.config(text="0")
        self.card_checks.sub_label.config(text="הבאה: --:--")

    def _start_stats_updater(self):
        def update():
            while True:
                try:
                    if self.session_start_time:
                        uptime = int(time.time() - self.session_start_time)
                        h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60
                        self.card_time.value_label.config(text=f"{h:02}:{m:02}:{s:02}")

                    listener_stats = self.listener.get_stats()
                    checks = listener_stats.get('checks_today', 0)
                    next_check = listener_stats.get('next_check')
                    self.card_checks.value_label.config(text=str(checks))
                    if next_check:
                        now = time.time()
                        if next_check > now:
                            remaining = int(next_check - now)
                            rm, rs = remaining // 60, remaining % 60
                            self.card_checks.sub_label.config(text=f"הבאה: עוד {rm}:{rs:02}")
                        else:
                            self.card_checks.sub_label.config(text="הבאה: כעת...")
                    else:
                         self.card_checks.sub_label.config(text="הבאה: --:--")

                    today_stats = self.db.get_stats()
                    week_stats = self.db.get_week_stats()
                    self.card_apartments.value_label.config(text=str(today_stats.get('today', 0)))
                    self.card_apartments.sub_label.config(text=f"שבוע: {week_stats.get('relevant', 0)}")

                    try:
                        trends = self.analytics.get_trends_today()
                        avg_price = trends.get('avg_price', 0)
                        pop_city = trends.get('popular_city', 'אין')
                        clean_city = re.sub(r'[^\w\s\(\)\'\"]', '', pop_city).strip()
                        if avg_price > 0:
                            self.card_trends.value_label.config(text=f"₪{avg_price:,}")
                        else:
                            self.card_trends.value_label.config(text="--")
                        self.card_trends.sub_label.config(text=f"עיר מובילה: {clean_city}")
                    except Exception:
                        pass
                except Exception:
                    pass
                time.sleep(1)
        threading.Thread(target=update, daemon=True).start()

    def show_apartments(self):
        # 1. סגירת חלון קודם
        if hasattr(self, 'apartments_window') and self.apartments_window and self.apartments_window.winfo_exists():
            self.apartments_window.destroy()

        # 2. שליפת נתונים
        posts = self.db.get_all_posts(relevant_only=True, limit=50)
        if not posts:
            messagebox.showinfo("אין דירות", "עדיין לא נמצאו דירות חדשות")
            return

        # 3. יצירת החלון
        window = tk.Toplevel(self.root)
        self.apartments_window = window
        window.title("📋 טבלת דירות מרוכזת")
        window.geometry("1350x650")
        window.configure(bg=COLORS['bg'])

        frame_table = tk.Frame(window, bg=COLORS['bg'])
        frame_table.pack(fill='both', expand=True, padx=15, pady=15)

        # --- עיצוב (כולל החזרת הסרגל המעוצב!) ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'), background=COLORS['secondary'],
                        foreground='white', relief='flat')
        style.configure("Treeview", rowheight=30, font=('Segoe UI', 10), background='white', fieldbackground='white',
                        borderwidth=0)
        style.map("Treeview", background=[('selected', COLORS['accent'])], foreground=[('selected', 'white')])

        # החזרת עיצוב סרגל הגלילה
        style.configure("Vertical.TScrollbar", background='#bdc3c7', troughcolor=COLORS['bg'], bordercolor=COLORS['bg'],
                        arrowcolor=COLORS['text'], relief='flat')
        style.map("Vertical.TScrollbar", background=[('active', COLORS['accent'])])

        # גלילה מעוצבת
        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", style="Vertical.TScrollbar")
        scrollbar.pack(side='right', fill='y')

        # --- הגדרת העמודות ---
        columns = ('index', 'author', 'city', 'neighborhood', 'street', 'price', 'rooms', 'phone', 'group', 'date',
                   'link', 'id')
        tree = ttk.Treeview(frame_table, columns=columns, show='headings', yscrollcommand=scrollbar.set)
        scrollbar.config(command=tree.yview)

        # --- כותרות ויישור (הוספנו anchor='e' גם לכותרות!) ---

        # עמודת האינדקס נשארת באמצע
        tree.column('index', width=40, anchor='center')
        tree.heading('index', text='#', anchor='center')

        # כל שאר העמודות - יישור לימין גם בתוכן וגם בכותרת
        tree.column('author', width=120, anchor='e')
        tree.heading('author', text='מפרסם', anchor='e')  # <--- הוספנו anchor='e'

        tree.column('city', width=90, anchor='e')
        tree.heading('city', text='עיר', anchor='e')  # <--- הוספנו anchor='e'

        tree.column('neighborhood', width=100, anchor='e')
        tree.heading('neighborhood', text='שכונה', anchor='e')  # <--- הוספנו anchor='e'

        tree.column('street', width=120, anchor='e')
        tree.heading('street', text='רחוב', anchor='e')  # <--- הוספנו anchor='e'

        tree.column('price', width=90, anchor='e')
        tree.heading('price', text='מחיר', anchor='e')  # <--- הוספנו anchor='e'

        tree.column('rooms', width=60, anchor='center')  # חדרים נראה טוב יותר באמצע
        tree.heading('rooms', text='חדרים', anchor='center')

        tree.column('phone', width=110, anchor='e')
        tree.heading('phone', text='טלפון', anchor='e')  # <--- הוספנו anchor='e'

        tree.column('group', width=160, anchor='e')
        tree.heading('group', text='קבוצה', anchor='e')  # <--- הוספנו anchor='e'

        tree.column('date', width=110, anchor='e')
        tree.heading('date', text='תאריך', anchor='e')  # <--- הוספנו anchor='e'

        # עמודות נסתרות
        tree.column('link', width=0, stretch=False)
        tree.column('id', width=0, stretch=False)

        tree.pack(fill='both', expand=True)
        tree.tag_configure('oddrow', background='white')
        tree.tag_configure('evenrow', background='#f2f6f8')

        status_var = tk.StringVar()

        # --- מילוי נתונים ---
        def populate_tree():
            for item in tree.get_children():
                tree.delete(item)

            current_posts = self.db.get_all_posts(relevant_only=True, limit=50)

            for i, post in enumerate(current_posts):
                author = post['author'] or "-"

                # פיצול מיקום לשלושה שדות
                city = post.get('city') or "-"
                neighborhood = "-"
                street = "-"

                loc = post.get('location', '')
                if loc:
                    # בדיקה: האם יש פסיק? (שכונה + רחוב)
                    if ',' in loc:
                        parts = [p.strip() for p in loc.split(',', 1)]
                        if len(parts) >= 2 and parts[0] and parts[1]:  # ← הוסף בדיקה!
                            neighborhood = parts[0]
                            street = parts[1]
                        else:
                            # פסיק אבל חסר חלק - התייחס כשכונה בלבד
                            neighborhood = parts[0] if parts[0] else loc

                    # אם אין פסיק - בדוק אם זה רחוב או שכונה
                    elif 'רחוב' in loc or 'רח\'' in loc or 'רח"' in loc:
                        street = loc
                    else:
                        neighborhood = loc

                # מחיר עם פסיקים
                price = "-"
                if post['price']:
                    try:
                        clean_num = int(str(post['price']).replace(',', '').replace('.', ''))
                        price = f"₪{clean_num:,}"
                    except (ValueError, TypeError):
                        price = str(post['price'])

                rooms = post['rooms'] or "-"
                phone = post['phone'] or "-"

                # קיצור שם קבוצה
                full_group = post.get('group_name') or "-"
                words = full_group.split()
                if len(words) > 3:
                    group_display = " ".join(words[:3]) + "..."
                else:
                    group_display = full_group

                # קיצור תאריך
                date_full = post.get('scanned_at') or ""
                date_display = date_full[5:16] if len(date_full) > 16 else date_full

                link = post['post_url']
                post_id = post.get('id', 0)

                row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'

                tree.insert('', 'end',
                            values=(i + 1, author, city, neighborhood, street, price, rooms, phone, group_display,
                                    date_display, link, post_id),
                            tags=(row_tag,))

            status_var.set(f"סה\"כ מוצגות: {len(current_posts)} דירות")

        populate_tree()

        # --- פונקציות עזר ---
        def delete_selected_post(event=None):
            selected_item = tree.selection()
            if not selected_item: return
            item = selected_item[0]
            values = tree.item(item, "values")
            author = values[1]
            post_url = values[10]

            if not messagebox.askyesno("מחיקה", f"למחוק פוסט של {author}?"): return
            try:
                import sqlite3
                conn = sqlite3.connect(self.db.db_path)
                cursor = conn.cursor()
                cursor.execute('DELETE FROM posts WHERE post_url = ?', (post_url,))
                conn.commit()
                conn.close()
                tree.delete(item)
                populate_tree()
                messagebox.showinfo("הצלחה", "הפוסט נמחק.")
            except Exception as e:
                messagebox.showerror("שגיאה", f"תקלה: {e}")

        def open_in_browser(event=None):
            selected_item = tree.selection()
            if not selected_item: return
            values = tree.item(selected_item[0], "values")
            url = values[10]
            if url and "http" in url: webbrowser.open(url)

        context_menu = tk.Menu(window, tearoff=0, font=('Segoe UI', 10))
        context_menu.add_command(label="🌐 פתח בדפדפן", command=open_in_browser)
        context_menu.add_separator()
        context_menu.add_command(label="🗑️ מחק דירה", command=delete_selected_post)

        def on_right_click(event):
            row_id = tree.identify_row(event.y)
            if row_id: tree.selection_set(row_id); context_menu.post(event.x_root, event.y_root)

        tree.bind("<Button-3>", on_right_click)
        tree.bind("<Double-1>", open_in_browser)
        tree.bind("<Delete>", delete_selected_post)

        # כפתורים למטה
        btn_frame = tk.Frame(window, bg=COLORS['bg'])
        btn_frame.pack(fill='x', padx=20, pady=(0, 10))
        tk.Button(btn_frame, text="סגור חלון", command=window.destroy, bg='white', relief='flat', width=12).pack(
            side='left')
        tk.Button(btn_frame, text="🔄 רענן", command=populate_tree, bg=COLORS['accent'], fg='white', relief='flat',
                  width=15).pack(side='right')

        status_bar = tk.Frame(window, bg='#e0e0e0', height=25)
        status_bar.pack(side='bottom', fill='x')
        tk.Label(status_bar, textvariable=status_var, bg='#e0e0e0', fg='#555').pack(side='right', padx=10)


    def export_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if filename:
            if self.db.export_to_csv(filename):
                messagebox.showinfo("הצלחה", "נשמר בהצלחה!")
                try: os.startfile(os.path.dirname(filename))
                except OSError: pass
            else: messagebox.showwarning("שגיאה", "אין נתונים לייצוא")

def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except Exception: pass
    app = GuardianGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
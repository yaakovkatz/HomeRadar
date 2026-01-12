"""
settings_dialog.py - חלון הגדרות מודרני
"""

import tkinter as tk
from tkinter import ttk, messagebox
from settings_manager import SettingsManager

# צבעים - אותם כמו ב-main.py
COLORS = {
    'primary': '#2c3e50',
    'secondary': '#34495e',
    'accent': '#3498db',
    'success': '#27ae60',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'bg': '#ecf0f1',
    'card': '#ffffff',
    'text': '#2c3e50',
    'text_light': '#7f8c8d',
    'sub_text': '#95a5a6'
}


class SettingsDialog:
    """חלון הגדרות עם tabs"""

    def __init__(self, parent):
        """
        Args:
            parent: החלון הראשי (root)
        """
        self.parent = parent
        self.settings = SettingsManager()

        # יצירת החלון
        self.window = tk.Toplevel(parent)
        self.window.title("⚙️ הגדרות מערכת")
        self.window.geometry("700x600")
        self.window.configure(bg=COLORS['bg'])

        # חלון מודלי (חוסם את החלון הראשי)
        self.window.transient(parent)
        self.window.grab_set()

        # בניית הממשק
        self._create_header()
        self._create_tabs()
        self._create_buttons()

        # טעינת ערכים נוכחיים
        self._load_current_values()

        # מרכוז החלון
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (700 // 2)
        y = (self.window.winfo_screenheight() // 2) - (600 // 2)
        self.window.geometry(f"700x600+{x}+{y}")

    def _create_header(self):
        """יצירת כותרת"""
        header = tk.Frame(self.window, bg=COLORS['primary'], height=70)
        header.pack(fill='x')
        header.pack_propagate(False)

        tk.Label(
            header,
            text="⚙️ הגדרות מערכת",
            font=('Segoe UI', 20, 'bold'),
            bg=COLORS['primary'],
            fg='white'
        ).pack(pady=20)

    def _create_tabs(self):
        """יצירת Tabs"""
        # Frame לכל התוכן
        content_frame = tk.Frame(self.window, bg=COLORS['bg'])
        content_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Notebook (Tabs)
        style = ttk.Style()
        style.theme_use('default')
        style.configure('TNotebook', background=COLORS['bg'], borderwidth=0)
        style.configure('TNotebook.Tab',
                        font=('Segoe UI', 11),
                        padding=[20, 10],
                        background=COLORS['card'])
        style.map('TNotebook.Tab',
                  background=[('selected', COLORS['accent'])],
                  foreground=[('selected', 'white')])

        self.notebook = ttk.Notebook(content_frame)
        self.notebook.pack(fill='both', expand=True)

        # יצירת 3 tabs
        self.tab_general = self._create_general_tab()
        self.tab_groups = self._create_groups_tab()
        self.tab_filters = self._create_filters_tab()

        self.notebook.add(self.tab_general, text='⚙️ כללי')
        self.notebook.add(self.tab_groups, text='📂 קבוצות')
        self.notebook.add(self.tab_filters, text='🚫 סינון')

    def _create_general_tab(self):
        """Tab הגדרות כלליות"""
        tab = tk.Frame(self.notebook, bg=COLORS['card'])

        # Frame פנימי עם padding
        inner = tk.Frame(tab, bg=COLORS['card'])
        inner.pack(fill='both', expand=True, padx=30, pady=30)

        # כותרת
        tk.Label(
            inner,
            text="הגדרות האזנה",
            font=('Segoe UI', 14, 'bold'),
            bg=COLORS['card'],
            fg=COLORS['primary']
        ).grid(row=0, column=0, columnspan=3, sticky='e', pady=(0, 20))

        # מרווח בדיקות - מינימום
        tk.Label(
            inner,
            text="⏱️ מרווח בדיקות מינימלי (שניות):",
            font=('Segoe UI', 10),
            bg=COLORS['card'],
            fg=COLORS['text']
        ).grid(row=1, column=0, sticky='e', padx=(0, 10), pady=10)

        self.check_min_entry = tk.Entry(
            inner,
            font=('Segoe UI', 11),
            width=10,
            relief='flat',
            bd=2
        )
        self.check_min_entry.grid(row=1, column=1, sticky='w', pady=10)

        tk.Label(
            inner,
            text="(360 = 6 דקות)",
            font=('Segoe UI', 9),
            bg=COLORS['card'],
            fg=COLORS['sub_text']
        ).grid(row=1, column=2, sticky='w', padx=(10, 0), pady=10)

        # מרווח בדיקות - מקסימום
        tk.Label(
            inner,
            text="⏱️ מרווח בדיקות מקסימלי (שניות):",
            font=('Segoe UI', 10),
            bg=COLORS['card'],
            fg=COLORS['text']
        ).grid(row=2, column=0, sticky='e', padx=(0, 10), pady=10)

        self.check_max_entry = tk.Entry(
            inner,
            font=('Segoe UI', 11),
            width=10,
            relief='flat',
            bd=2
        )
        self.check_max_entry.grid(row=2, column=1, sticky='w', pady=10)

        tk.Label(
            inner,
            text="(480 = 8 דקות)",
            font=('Segoe UI', 9),
            bg=COLORS['card'],
            fg=COLORS['sub_text']
        ).grid(row=2, column=2, sticky='w', padx=(10, 0), pady=10)

        # שעות פעילות - התחלה
        tk.Label(
            inner,
            text="🕐 שעת התחלה:",
            font=('Segoe UI', 10),
            bg=COLORS['card'],
            fg=COLORS['text']
        ).grid(row=3, column=0, sticky='e', padx=(0, 10), pady=10)

        self.hour_start_entry = tk.Entry(
            inner,
            font=('Segoe UI', 11),
            width=10,
            relief='flat',
            bd=2
        )
        self.hour_start_entry.grid(row=3, column=1, sticky='w', pady=10)

        tk.Label(
            inner,
            text="(0-23)",
            font=('Segoe UI', 9),
            bg=COLORS['card'],
            fg=COLORS['sub_text']
        ).grid(row=3, column=2, sticky='w', padx=(10, 0), pady=10)

        # שעות פעילות - סיום
        tk.Label(
            inner,
            text="🕐 שעת סיום:",
            font=('Segoe UI', 10),
            bg=COLORS['card'],
            fg=COLORS['text']
        ).grid(row=4, column=0, sticky='e', padx=(0, 10), pady=10)

        self.hour_end_entry = tk.Entry(
            inner,
            font=('Segoe UI', 11),
            width=10,
            relief='flat',
            bd=2
        )
        self.hour_end_entry.grid(row=4, column=1, sticky='w', pady=10)

        tk.Label(
            inner,
            text="(0-23)",
            font=('Segoe UI', 9),
            bg=COLORS['card'],
            fg=COLORS['sub_text']
        ).grid(row=4, column=2, sticky='w', padx=(10, 0), pady=10)

        # פוסטים לקריאה
        tk.Label(
            inner,
            text="📊 כמות פוסטים לקריאה:",
            font=('Segoe UI', 10),
            bg=COLORS['card'],
            fg=COLORS['text']
        ).grid(row=5, column=0, sticky='e', padx=(0, 10), pady=10)

        self.posts_read_entry = tk.Entry(
            inner,
            font=('Segoe UI', 11),
            width=10,
            relief='flat',
            bd=2
        )
        self.posts_read_entry.grid(row=5, column=1, sticky='w', pady=10)

        tk.Label(
            inner,
            text="(מומלץ: 3-7)",
            font=('Segoe UI', 9),
            bg=COLORS['card'],
            fg=COLORS['sub_text']
        ).grid(row=5, column=2, sticky='w', padx=(10, 0), pady=10)

        return tab

    def _create_groups_tab(self):
        """Tab ניהול קבוצות"""
        tab = tk.Frame(self.notebook, bg=COLORS['card'])

        inner = tk.Frame(tab, bg=COLORS['card'])
        inner.pack(fill='both', expand=True, padx=30, pady=30)

        tk.Label(
            inner,
            text="📂 קבוצות פייסבוק",
            font=('Segoe UI', 14, 'bold'),
            bg=COLORS['card'],
            fg=COLORS['primary']
        ).pack(anchor='e', pady=(0, 20))

        tk.Label(
            inner,
            text="(יישום מלא בגרסה הבאה)",
            font=('Segoe UI', 10),
            bg=COLORS['card'],
            fg=COLORS['sub_text']
        ).pack(anchor='center', pady=20)

        return tab

    def _create_filters_tab(self):
        """Tab סינון"""
        tab = tk.Frame(self.notebook, bg=COLORS['card'])

        inner = tk.Frame(tab, bg=COLORS['card'])
        inner.pack(fill='both', expand=True, padx=30, pady=30)

        tk.Label(
            inner,
            text="🚫 סינון פוסטים",
            font=('Segoe UI', 14, 'bold'),
            bg=COLORS['card'],
            fg=COLORS['primary']
        ).pack(anchor='e', pady=(0, 20))

        tk.Label(
            inner,
            text="(יישום מלא בגרסה הבאה)",
            font=('Segoe UI', 10),
            bg=COLORS['card'],
            fg=COLORS['sub_text']
        ).pack(anchor='center', pady=20)

        return tab

    def _create_buttons(self):
        """כפתורי שמירה וביטול"""
        button_frame = tk.Frame(self.window, bg=COLORS['bg'])
        button_frame.pack(fill='x', padx=20, pady=(0, 20))

        # כפתור ביטול
        tk.Button(
            button_frame,
            text="❌ ביטול",
            font=('Segoe UI', 11),
            bg=COLORS['secondary'],
            fg='white',
            relief='flat',
            cursor='hand2',
            command=self.cancel,
            width=15,
            height=2
        ).pack(side='left', padx=5)

        # כפתור שמירה
        tk.Button(
            button_frame,
            text="💾 שמור ועדכן",
            font=('Segoe UI', 11, 'bold'),
            bg=COLORS['success'],
            fg='white',
            relief='flat',
            cursor='hand2',
            command=self.save,
            width=15,
            height=2
        ).pack(side='right', padx=5)

    def _load_current_values(self):
        """טוען ערכים נוכחיים מההגדרות"""
        # מרווחי בדיקות
        self.check_min_entry.insert(0, str(self.settings.get('listener.check_interval_min', 360)))
        self.check_max_entry.insert(0, str(self.settings.get('listener.check_interval_max', 480)))

        # שעות פעילות
        self.hour_start_entry.insert(0, str(self.settings.get('listener.active_hours_start', 8)))
        self.hour_end_entry.insert(0, str(self.settings.get('listener.active_hours_end', 23)))

        # פוסטים לקריאה
        self.posts_read_entry.insert(0, str(self.settings.get('listener.posts_to_read', 3)))

    def save(self):
        """שמירת ההגדרות"""
        try:
            # קריאת ערכים
            check_min = int(self.check_min_entry.get())
            check_max = int(self.check_max_entry.get())
            hour_start = int(self.hour_start_entry.get())
            hour_end = int(self.hour_end_entry.get())
            posts_read = int(self.posts_read_entry.get())

            # ולידציה בסיסית
            if check_min >= check_max:
                messagebox.showerror("שגיאה", "מינימום חייב להיות קטן ממקסימום!")
                return

            if not (0 <= hour_start <= 23) or not (0 <= hour_end <= 23):
                messagebox.showerror("שגיאה", "שעות חייבות להיות בין 0 ל-23!")
                return

            if posts_read < 1 or posts_read > 20:
                messagebox.showerror("שגיאה", "פוסטים לקריאה: 1-20!")
                return

            # שמירה!
            self.settings.set('listener.check_interval_min', check_min)
            self.settings.set('listener.check_interval_max', check_max)
            self.settings.set('listener.active_hours_start', hour_start)
            self.settings.set('listener.active_hours_end', hour_end)
            self.settings.set('listener.posts_to_read', posts_read)

            # הודעה
            messagebox.showinfo("✅ הצלחה", "ההגדרות נשמרו ועודכנו!\n\nהשינויים ייכנסו לתוקף בבדיקה הבאה.")

            # סגירת החלון
            self.window.destroy()

        except ValueError:
            messagebox.showerror("שגיאה", "יש להזין מספרים בלבד!")

    def cancel(self):
        """ביטול ללא שמירה"""
        self.window.destroy()
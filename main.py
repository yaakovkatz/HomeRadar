"""
main.py - ממשק משתמש סופי בהחלט (עיצוב מתוקן + יומן פעילות חכם RTL)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
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
        self.root.geometry("1150x850")
        self.root.configure(bg=COLORS['bg'])

        self.listener = FacebookListener()
        self.listener.set_status_callback(self.log_status)
        self.db = PostDatabase()
        self.analytics = Analytics()
        self.session_start_time = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        # בניית הממשק
        self._create_header()
        self._create_dashboard()
        self._create_controls()
        self._create_log_area()

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

        tk.Label(title_frame, text="Facebook Guardian", font=('Segoe UI', 24, 'bold'), bg=COLORS['primary'], fg='white').pack(anchor='e')
        tk.Label(title_frame, text="מערכת ניטור נדל\"ן בזמן אמת", font=('Segoe UI', 11), bg=COLORS['primary'], fg='#bdc3c7').pack(anchor='e', pady=(0, 0))

    def _create_dashboard(self):
        dashboard = tk.Frame(self.root, bg=COLORS['bg'])
        dashboard.pack(fill='x', padx=15, pady=20)

        # כרטיסים
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
        controls.pack(fill='x', padx=20, pady=(0, 15))

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

    def _create_log_area(self):
        log_frame = tk.Frame(self.root, bg=COLORS['bg'], padx=20)
        log_frame.pack(fill='both', expand=True, pady=(0, 20))

        header_frame = tk.Frame(log_frame, bg=COLORS['bg'])
        header_frame.pack(fill='x', pady=(0, 5))
        tk.Label(header_frame, text="📝 יומן פעילות", font=('Segoe UI', 11, 'bold'), bg=COLORS['bg'], fg=COLORS['primary']).pack(side='right')

        self.log_text = scrolledtext.ScrolledText(log_frame, font=('Consolas', 10), height=12,
                                                bg='white', fg=COLORS['text'], relief='flat', padx=10, pady=10)
        self.log_text.pack(fill='both', expand=True)

        # הגדרת תגיות עיצוב
        self.log_text.tag_config('INFO', foreground='gray')
        self.log_text.tag_config('SUCCESS', foreground=COLORS['success'])
        self.log_text.tag_config('ERROR', foreground=COLORS['danger'])
        self.log_text.tag_config('WARNING', foreground=COLORS['warning'])

        # מחזירים ליישור לשמאל, כדי שהשעון יהיה בצד הנכון
        self.log_text.tag_config('RTL', justify='left')

    def log_status(self, message, level='INFO'):
        """לוג עם תמיכה בעברית"""
        clean_msg = re.sub(r'^\[.*?\]\s*', '', str(message))
        timestamp = datetime.now().strftime("%H:%M:%S")

        # פשוט מוסיפים את ההודעה כמו שהיא
        full_msg = f"[{timestamp}] {clean_msg}\n"
        self.log_text.insert('end', full_msg, level)
        self.log_text.see('end')

    def manage_groups_placeholder(self):
        """פותח חלון ניהול קבוצות"""
        from groups_dialog import GroupsDialog

        # האם המערכת פעילה?
        read_only = self.listener.is_listening

        # פתיחת חלון
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

        self.log_status("מאתחל מנוע האזנה...", "INFO") # לוג יזום

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

        # לוג יזום של עצירה
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
        """מעדכן את כל הכרטיסים"""
        def update():
            while True:
                try:
                    # 1. זמן פעילות
                    if self.session_start_time:
                        uptime = int(time.time() - self.session_start_time)
                        h, m, s = uptime // 3600, (uptime % 3600) // 60, uptime % 60
                        self.card_time.value_label.config(text=f"{h:02}:{m:02}:{s:02}")

                    # 2. נתונים מהליסנר (בדיקות)
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

                    # 3. נתונים מהדאטאבייס (דירות)
                    today_stats = self.db.get_stats()
                    week_stats = self.db.get_week_stats()

                    self.card_apartments.value_label.config(text=str(today_stats.get('today', 0)))
                    self.card_apartments.sub_label.config(text=f"שבוע: {week_stats.get('relevant', 0)}")

                    # 4. טרנדים (מחיר ממוצע)
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
                    except:
                        pass

                except Exception as e:
                    pass
                time.sleep(1)

        threading.Thread(target=update, daemon=True).start()

    def show_apartments(self):
        # שליפת נתונים
        posts = self.db.get_all_posts(relevant_only=True, limit=50)

        if not posts:
            messagebox.showinfo("אין דירות", "עדיין לא נמצאו דירות חדשות")
            return

        window = tk.Toplevel(self.root)
        window.title("📋 דירות שנמצאו")
        window.geometry("1100x650")
        window.configure(bg=COLORS['bg'])

        # --- מסגרת לטבלה ---
        frame_table = tk.Frame(window, bg=COLORS['bg'])
        frame_table.pack(fill='both', expand=True, padx=20, pady=20)

        # --- עיצוב (Style) ---
        style = ttk.Style()
        style.theme_use('clam')  # ערכת נושא שמאפשרת שינויי צבע

        # 1. עיצוב כותרות
        style.configure("Treeview.Heading",
                        font=('Segoe UI', 11, 'bold'),
                        background=COLORS['secondary'],
                        foreground='white',
                        relief='flat')

        # 2. עיצוב שורות
        style.configure("Treeview",
                        rowheight=35,
                        font=('Segoe UI', 10),
                        background='white',
                        fieldbackground='white',
                        borderwidth=0)

        style.map("Treeview",
                  background=[('selected', COLORS['accent'])],
                  foreground=[('selected', 'white')])

        # 3. --- עיצוב פס גלילה (Scrollbar) עדין ---
        style.configure("Vertical.TScrollbar",
                        background='#bdc3c7',  # צבע הידית (אפור בהיר ועדין)
                        troughcolor=COLORS['bg'],  # צבע המסלול (זהה לרקע - נראה שקוף)
                        bordercolor=COLORS['bg'],  # מעלים את המסגרת
                        lightcolor=COLORS['bg'],  # מעלים הצללות
                        darkcolor=COLORS['bg'],  # מעלים הצללות
                        arrowcolor=COLORS['text'],  # צבע החצים (אפור כהה)
                        relief='flat')  # מראה שטוח ללא תלת-ממד

        # כשעוברים עם העכבר על פס הגלילה - הוא יהפוך לכחול
        style.map("Vertical.TScrollbar",
                  background=[('active', COLORS['accent'])])

        # יצירת פס הגלילה עם העיצוב החדש
        scrollbar = ttk.Scrollbar(frame_table, orient="vertical", style="Vertical.TScrollbar")
        scrollbar.pack(side='right', fill='y')

        # הגדרת העמודות - עם קבוצה! ← חדש!
        columns = ('index', 'author', 'city', 'price', 'rooms', 'phone', 'group', 'date', 'link')
        tree = ttk.Treeview(frame_table, columns=columns, show='headings', yscrollcommand=scrollbar.set)

        # חיבור הגלילה לטבלה
        scrollbar.config(command=tree.yview)

        # --- כותרות ורוחב עמודות ---
        tree.heading('index', text='#', anchor='center')
        tree.column('index', width=40, anchor='center', stretch=False)

        tree.heading('author', text='מפרסם', anchor='e')
        tree.column('author', width=130, anchor='e')

        tree.heading('city', text='עיר', anchor='e')
        tree.column('city', width=140, anchor='e')

        tree.heading('price', text='מחיר', anchor='e')
        tree.column('price', width=110, anchor='e')

        tree.heading('rooms', text='חדרים', anchor='center')
        tree.column('rooms', width=70, anchor='center')

        tree.heading('phone', text='טלפון', anchor='e')
        tree.column('phone', width=110, anchor='e')

        tree.heading('group', text='קבוצה', anchor='e')
        tree.column('group', width=150, anchor='e')

        tree.heading('date', text='תאריך', anchor='center')
        tree.column('date', width=140, anchor='center')

        tree.heading('link', text='Link', anchor='w')
        tree.column('link', width=0, stretch=False)

        tree.pack(fill='both', expand=True)

        # --- צבעי זברה ---
        tree.tag_configure('oddrow', background='white')
        tree.tag_configure('evenrow', background='#f4f6f7')

        # --- מילוי נתונים ---
        for i, post in enumerate(posts):
            author = post['author'] or "-"
            city = post['city'] or "-"

            price_raw = post['price']
            if price_raw:
                try:
                    clean_num = int(str(price_raw).replace(',', '').replace('.', ''))
                    price = f"₪{clean_num:,}"
                except:
                    price = str(price_raw)
            else:
                price = "-"

            rooms = post['rooms'] or "-"
            phone = post['phone'] or "-"
            group = post['group_name'] or "-"  # ✨ הוסף את השורה הזו!
            date = post['scanned_at'][:16] if post['scanned_at'] else ""
            link = post['post_url']

            row_tag = 'evenrow' if i % 2 == 0 else 'oddrow'
            tree.insert('', 'end', values=(i + 1, author, city, price, rooms, phone, group, date, link),
                        tags=(row_tag,))

        # --- אינטראקציה ---
        def on_double_click(event):
            try:
                item = tree.selection()
                if not item: return
                values = tree.item(item, "values")
                url = values[8]
                print(f"Opening: {url}")
                if url and "http" in url:
                    webbrowser.open(url)
                else:
                    messagebox.showwarning("שגיאה", "לא נמצא קישור תקין")
            except Exception as e:
                print(f"Error: {e}")

        tree.bind("<Double-1>", on_double_click)

        # --- Footer ---
        footer_frame = tk.Frame(window, bg=COLORS['bg'])
        footer_frame.pack(fill='x', pady=10)

        tk.Label(footer_frame, text="💡 דאבל-קליק לפתיחת פוסט בדפדפן",
                 bg=COLORS['bg'], fg=COLORS['text_light'], font=('Segoe UI', 9)).pack()

        tk.Button(footer_frame, text="סגור חלון", command=window.destroy,
                  bg='white', fg=COLORS['text'], relief='flat', bd=1).pack(pady=5)

    def export_csv(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if filename:
            if self.db.export_to_csv(filename):
                messagebox.showinfo("הצלחה", "נשמר בהצלחה!")
                try:
                    os.startfile(os.path.dirname(filename))
                except: pass
            else:
                messagebox.showwarning("שגיאה", "אין נתונים לייצוא")

def main():
    root = tk.Tk()
    try:
        from ctypes import windll
        windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    app = GuardianGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
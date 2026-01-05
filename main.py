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
        """לוג מיושר לשמאל - עם תיקון לעברית שלא תתהפך"""

        # ניקוי זמנים כפולים
        clean_msg = re.sub(r'^\[.*?\]\s*', '', str(message))
        timestamp = datetime.now().strftime("%H:%M:%S")

        has_hebrew = any("\u0590" <= c <= "\u05ea" for c in clean_msg)

        # הטריק: התו הנסתר \u200f נמצא *אחרי* השעה
        # זה משאיר את השעה משמאל, אבל מסדר את העברית שתבוא אחריה טוב
        if has_hebrew:
            full_msg = f"[{timestamp}] \u200f{clean_msg}\n"
            # משתמשים בתגית RTL שמוגדרת ליישור לשמאל (תכף נוודא את זה)
            self.log_text.insert('end', full_msg, ('RTL', level))
        else:
            full_msg = f"[{timestamp}] {clean_msg}\n"
            self.log_text.insert('end', full_msg, level)

        self.log_text.see('end')

    def manage_groups_placeholder(self):
        messagebox.showinfo("בקרוב", "ניהול קבוצות יהיה זמין בגרסה הבאה!")

    # --- לוגיקה ---

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
        posts = self.db.get_all_posts(relevant_only=True, limit=50)

        if not posts:
            messagebox.showinfo("אין דירות", "עדיין לא נמצאו דירות חדשות")
            return

        window = tk.Toplevel(self.root)
        window.title("📋 דירות שנמצאו")
        window.geometry("1000x600")

        scrollbar = ttk.Scrollbar(window)
        scrollbar.pack(side='right', fill='y')

        columns = ('author', 'city', 'price', 'rooms', 'phone', 'date', 'link')
        tree = ttk.Treeview(window, columns=columns, show='headings', yscrollcommand=scrollbar.set)

        style = ttk.Style()
        style.configure("Treeview.Heading", font=('Segoe UI', 10, 'bold'))
        style.configure("Treeview", rowheight=30, font=('Segoe UI', 10))

        tree.heading('author', text='מפרסם', anchor='e')
        tree.heading('city', text='עיר', anchor='e')
        tree.heading('price', text='מחיר', anchor='e')
        tree.heading('rooms', text='חדרים', anchor='center')
        tree.heading('phone', text='טלפון', anchor='e')
        tree.heading('date', text='תאריך', anchor='center')

        tree.column('author', width=120, anchor='e')
        tree.column('city', width=150, anchor='e')
        tree.column('price', width=100, anchor='e')
        tree.column('rooms', width=80, anchor='center')
        tree.column('phone', width=120, anchor='e')
        tree.column('date', width=150, anchor='center')
        tree.column('link', width=0, stretch=False)

        scrollbar.config(command=tree.yview)
        tree.pack(padx=10, pady=10, fill='both', expand=True)

        for post in posts:
            author = post['author'] or "לא צוין"
            city = post['city'] or "לא צוין"
            price = f"₪{post['price']}" if post['price'] else "לא צוין"
            rooms = post['rooms'] or "לא צוין"
            phone = post['phone'] or "לא צוין"
            date = post['scanned_at'][:16] if post['scanned_at'] else ""
            link = post['post_url']

            tree.insert('', 'end', values=(author, city, price, rooms, phone, date, link))

        def on_double_click(event):
            item = tree.selection()
            if not item: return
            values = tree.item(item, "values")
            url = values[6]
            if url and "http" in url:
                webbrowser.open(url)

        tree.bind("<Double-1>", on_double_click)

        tk.Label(window, text="💡 דאבל-קליק לפתיחת פוסט", fg="gray", font=('Segoe UI', 9)).pack(pady=5)
        tk.Button(window, text="סגור", command=window.destroy).pack(pady=5)

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
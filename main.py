"""
main.py - ממשק משתמש למצב Guardian (האזנה רציפה)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from listener import FacebookListener
from database import PostDatabase
import threading
from datetime import datetime
import os


class GuardianGUI:
    """ממשק גרפי למצב Guardian"""

    def __init__(self, root):
        """אתחול הממשק"""
        self.root = root
        self.root.title("🏠 Facebook Guardian")
        self.root.geometry("800x700")
        self.root.configure(bg='#f0f0f0')

        self.listener = FacebookListener()
        self.listener.set_status_callback(self.log_status)

        self.db = PostDatabase()

        # טיפול בסגירת חלון
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

        self._create_widgets()
        self._start_stats_updater()

    def on_closing(self):
        """מטפל בסגירת החלון"""
        if self.listener.is_listening:
            result = messagebox.askyesno(
                "האזנה פעילה",
                "ההאזנה עדיין פעילה.\n\nהאם לעצור ולסגור?"
            )
            if not result:
                return

        self.log_status("🧹 מנקה ויוצא...")

        # עצור האזנה ונקה
        self.listener.force_cleanup()

        # סגור חלון
        self.root.destroy()

    def _create_widgets(self):
        """יוצר את כל רכיבי הממשק"""

        # כותרת
        title_frame = tk.Frame(self.root, bg='#2c3e50', height=70)
        title_frame.pack(fill='x')
        title_frame.pack_propagate(False)

        tk.Label(
            title_frame,
            text="🏠 Facebook Guardian",
            font=('Arial', 20, 'bold'),
            bg='#2c3e50',
            fg='white'
        ).pack(side='left', padx=20, pady=15)

        tk.Label(
            title_frame,
            text="מצב זהיר - האזנה רציפה",
            font=('Arial', 10),
            bg='#2c3e50',
            fg='#ecf0f1'
        ).pack(side='left', padx=0, pady=15)

        # מסגרת ראשית
        main_frame = tk.Frame(self.root, bg='#f0f0f0')
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        # --- פאנל סטטוס ---
        status_frame = tk.LabelFrame(
            main_frame,
            text="📊 סטטוס",
            font=('Arial', 11, 'bold'),
            bg='#f0f0f0',
            fg='#2c3e50'
        )
        status_frame.pack(fill='x', pady=(0, 10))

        status_inner = tk.Frame(status_frame, bg='#f0f0f0')
        status_inner.pack(padx=15, pady=15)

        # משתנים לסטטוס
        self.status_label = tk.Label(
            status_inner,
            text="📡 מצב: לא מאזין",
            font=('Arial', 12, 'bold'),
            bg='#f0f0f0',
            fg='#e74c3c'
        )
        self.status_label.grid(row=0, column=0, columnspan=2, pady=(0, 10), sticky='w')

        # סטטיסטיקות
        tk.Label(status_inner, text="🟢 דירות היום:", font=('Arial', 10), bg='#f0f0f0').grid(row=1, column=0, sticky='w', pady=2)
        self.relevant_label = tk.Label(status_inner, text="0", font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#27ae60')
        self.relevant_label.grid(row=1, column=1, sticky='w', padx=10, pady=2)

        tk.Label(status_inner, text="🔴 סוננו:", font=('Arial', 10), bg='#f0f0f0').grid(row=2, column=0, sticky='w', pady=2)
        self.blacklisted_label = tk.Label(status_inner, text="0", font=('Arial', 10, 'bold'), bg='#f0f0f0', fg='#e74c3c')
        self.blacklisted_label.grid(row=2, column=1, sticky='w', padx=10, pady=2)

        tk.Label(status_inner, text="📈 בדיקות:", font=('Arial', 10), bg='#f0f0f0').grid(row=3, column=0, sticky='w', pady=2)
        self.checks_label = tk.Label(status_inner, text="0", font=('Arial', 10, 'bold'), bg='#f0f0f0')
        self.checks_label.grid(row=3, column=1, sticky='w', padx=10, pady=2)

        tk.Label(status_inner, text="⏱️ בדיקה אחרונה:", font=('Arial', 10), bg='#f0f0f0').grid(row=4, column=0, sticky='w', pady=2)
        self.last_check_label = tk.Label(status_inner, text="-", font=('Arial', 10), bg='#f0f0f0')
        self.last_check_label.grid(row=4, column=1, sticky='w', padx=10, pady=2)

        tk.Label(status_inner, text="⏭️ בדיקה הבאה:", font=('Arial', 10), bg='#f0f0f0').grid(row=5, column=0, sticky='w', pady=2)
        self.next_check_label = tk.Label(status_inner, text="-", font=('Arial', 10), bg='#f0f0f0')
        self.next_check_label.grid(row=5, column=1, sticky='w', padx=10, pady=2)

        # --- כפתורי פעולה ---
        buttons_frame = tk.Frame(main_frame, bg='#f0f0f0')
        buttons_frame.pack(fill='x', pady=(0, 10))

        self.start_button = tk.Button(
            buttons_frame,
            text="▶️ התחל האזנה",
            font=('Arial', 12, 'bold'),
            bg='#27ae60',
            fg='white',
            command=self.start_listening,
            cursor='hand2',
            relief='raised',
            bd=3,
            padx=20,
            pady=10
        )
        self.start_button.pack(side='left', padx=5, expand=True, fill='x')

        self.stop_button = tk.Button(
            buttons_frame,
            text="⏹️ עצור",
            font=('Arial', 12, 'bold'),
            bg='#e74c3c',
            fg='white',
            command=self.stop_listening,
            cursor='hand2',
            relief='raised',
            bd=3,
            padx=20,
            pady=10,
            state='disabled'
        )
        self.stop_button.pack(side='left', padx=5, expand=True, fill='x')

        # שורה שנייה של כפתורים
        buttons_frame2 = tk.Frame(main_frame, bg='#f0f0f0')
        buttons_frame2.pack(fill='x', pady=(0, 10))

        tk.Button(
            buttons_frame2,
            text="📋 הצג דירות",
            font=('Arial', 11, 'bold'),
            bg='#3498db',
            fg='white',
            command=self.show_apartments,
            cursor='hand2',
            relief='raised',
            bd=2,
            padx=15,
            pady=8
        ).pack(side='left', padx=5, expand=True, fill='x')

        tk.Button(
            buttons_frame2,
            text="💾 ייצא CSV",
            font=('Arial', 11, 'bold'),
            bg='#9b59b6',
            fg='white',
            command=self.export_csv,
            cursor='hand2',
            relief='raised',
            bd=2,
            padx=15,
            pady=8
        ).pack(side='left', padx=5, expand=True, fill='x')

        # --- אזור לוג ---
        log_frame = tk.LabelFrame(
            main_frame,
            text="📝 לוג פעילות",
            font=('Arial', 10, 'bold'),
            bg='#f0f0f0'
        )
        log_frame.pack(fill='both', expand=True)

        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            font=('Courier New', 9),
            height=15,
            wrap='word',
            bg='#2c3e50',
            fg='#ecf0f1',
            insertbackground='white'
        )
        self.log_text.pack(padx=10, pady=10, fill='both', expand=True)

        # הודעת פתיחה
        self.log_status("🏠 ברוך הבא ל-Facebook Guardian!")
        self.log_status("לחץ 'התחל האזנה' כדי להתחיל")
        self.log_status("-" * 60)

    def log_status(self, message):
        """מוסיף הודעה ללוג"""
        self.log_text.insert('end', f"{message}\n")
        self.log_text.see('end')
        self.root.update_idletasks()

    def start_listening(self):
        """מתחיל האזנה"""
        if self.listener.is_listening:
            self.log_status("⚠️ כבר מאזין!")
            return

        if self.listener.is_cleaning:
            messagebox.showwarning(
                "המתן...",
                "מנקה משאבים מהרצה קודמת.\nנסה שוב בעוד כמה שניות."
            )
            return

        self.start_button.config(state='disabled', text="⏳ פותח...")
        self.stop_button.config(state='disabled')
        self.status_label.config(text="📡 מצב: מפעיל...", fg='#f39c12')

        # התחלה ב-thread
        def start_thread():
            success = self.listener.start_listening()

            # בדיקה אם הצליח להתחיל
            import time
            time.sleep(2)  # חכה קצת

            if success and self.listener.is_listening and self.listener.scraper:
                # הצליח!
                self.start_button.config(state='disabled', text="▶️ התחל האזנה")
                self.stop_button.config(state='normal')
                self.status_label.config(text="📡 מצב: מאזין...", fg='#27ae60')
            else:
                # נכשל
                self.start_button.config(state='normal', text="▶️ התחל האזנה")
                self.stop_button.config(state='disabled')
                self.status_label.config(text="📡 מצב: שגיאה בהפעלה", fg='#e74c3c')
                messagebox.showerror(
                    "שגיאה",
                    "נכשל לפתוח דפדפן!\n\nבדוק את הלוג לפרטים."
                )

        threading.Thread(target=start_thread, daemon=True).start()

    def stop_listening(self):
        """עוצר האזנה"""
        if not self.listener.is_listening:
            self.log_status("⚠️ לא מאזין כרגע")
            return

        self.stop_button.config(state='disabled', text="⏳ עוצר...")
        self.status_label.config(text="📡 מצב: מנקה...", fg='#f39c12')

        # עצירה ב-thread
        def stop_thread():
            self.listener.stop_listening()

            # חכה שהניקוי יסתיים
            import time
            time.sleep(2)

            # עדכון ממשק
            self.start_button.config(state='normal')
            self.stop_button.config(state='disabled', text="⏹️ עצור")
            self.status_label.config(text="📡 מצב: לא מאזין", fg='#e74c3c')

        threading.Thread(target=stop_thread, daemon=True).start()

    def _start_stats_updater(self):
        """מעדכן סטטיסטיקות כל 2 שניות"""
        def update():
            while True:
                try:
                    stats = self.listener.get_stats()

                    # עדכון תוויות
                    self.relevant_label.config(text=str(stats.get('today_in_db', 0)))
                    self.blacklisted_label.config(text=str(stats.get('blacklisted', 0)))
                    self.checks_label.config(text=str(stats.get('checks_today', 0)))

                    # בדיקה אחרונה
                    if stats.get('last_check'):
                        last = stats['last_check'].strftime("%H:%M:%S")
                        self.last_check_label.config(text=last)

                    # בדיקה הבאה
                    if stats.get('next_check'):
                        import time
                        seconds_left = int(stats['next_check'] - time.time())
                        if seconds_left > 0:
                            minutes = seconds_left // 60
                            secs = seconds_left % 60
                            self.next_check_label.config(text=f"עוד {minutes}:{secs:02d}")

                except:
                    pass

                import time
                time.sleep(2)

        thread = threading.Thread(target=update, daemon=True)
        thread.start()

    def show_apartments(self):
        """מציג חלון עם דירות"""
        posts = self.db.get_all_posts(relevant_only=True, limit=50)

        if not posts:
            messagebox.showinfo("אין דירות", "עדיין לא נמצאו דירות חדשות")
            return

        # חלון חדש
        window = tk.Toplevel(self.root)
        window.title("📋 דירות שנמצאו")
        window.geometry("900x600")

        # טבלה
        tree = ttk.Treeview(window, columns=('תוכן', 'תאריך'), show='headings', height=20)
        tree.heading('תוכן', text='תוכן הפוסט')
        tree.heading('תאריך', text='תאריך')
        tree.column('תוכן', width=700)
        tree.column('תאריך', width=150)

        for post in posts:
            content = post['content'][:100] + "..." if len(post['content']) > 100 else post['content']
            date = post['scanned_at'][:16] if post['scanned_at'] else ""
            tree.insert('', 'end', values=(content, date))

        tree.pack(padx=10, pady=10, fill='both', expand=True)

        # כפתור סגירה
        tk.Button(
            window,
            text="סגור",
            command=window.destroy
        ).pack(pady=10)

    def export_csv(self):
        """מייצא ל-CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"apartments_{datetime.now().strftime('%Y%m%d')}.csv"
        )

        if filename:
            success = self.db.export_to_csv(filename, relevant_only=True)
            if success:
                messagebox.showinfo("הצלחה", f"הקובץ נשמר ב:\n{filename}")
                os.startfile(os.path.dirname(filename))
            else:
                messagebox.showwarning("אזהרה", "אין נתונים לייצוא")


def main():
    """פונקציה ראשית"""
    root = tk.Tk()
    app = GuardianGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
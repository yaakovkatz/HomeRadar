"""
groups_dialog.py - חלון ניהול קבוצות (עיצוב שורה חכמה - תיקון תצוגה)
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import webbrowser

# --- צבעים מודרניים ---
COLORS = {
    'primary': '#2c3e50',
    'accent': '#3498db',
    'success': '#27ae60',
    'danger': '#e74c3c',
    'warning': '#f39c12',
    'bg': '#f8f9fa',        # רקע כללי אפור בהיר
    'card': '#ffffff',      # רקע כרטיס לבן
    'card_border': '#dcdcdc', # גבול אפור עדין
    'text': '#2c3e50',
    'text_light': '#7f8c8d',
}

class GroupsDialog:
    def __init__(self, parent, read_only=False):
        self.window = tk.Toplevel(parent)
        self.read_only = read_only

        title = "👀 צפייה בקבוצות" if read_only else "👥 ניהול קבוצות"
        self.window.title(title)
        self.window.geometry("800x600")
        self.window.configure(bg=COLORS['bg'])
        self.window.resizable(False, False)

        self.config_path = "config.json"
        self.groups_urls = []
        self.groups_names = []
        self.groups_active = []

        self._load_groups()
        self._create_ui()

        self.window.transient(parent)
        self.window.grab_set()

    def _load_groups(self):
        """טוען קבוצות מ-config.json"""
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                self.groups_urls = config.get('groups_urls', [])
                self.groups_names = config.get('groups_names', [])
                self.groups_active = config.get('groups_active', [True] * len(self.groups_urls))

                # השלמות
                while len(self.groups_names) < len(self.groups_urls):
                    self.groups_names.append(f"קבוצה {len(self.groups_names) + 1}")
                while len(self.groups_active) < len(self.groups_urls):
                    self.groups_active.append(True)

    def _save_groups(self):
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            config['groups_urls'] = self.groups_urls
            config['groups_names'] = self.groups_names
            config['groups_active'] = self.groups_active
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            messagebox.showerror("שגיאה", f"נכשל לשמור:\n{str(e)}")
            return False

    def _create_ui(self):
        # --- כותרת ---
        header = tk.Frame(self.window, bg=COLORS['primary'], height=70)
        header.pack(fill='x')
        header.pack_propagate(False)

        title_text = "👀 צפייה בקבוצות" if self.read_only else "👥 ניהול קבוצות"
        tk.Label(header, text=title_text, font=('Segoe UI', 16, 'bold'),
                bg=COLORS['primary'], fg='white').pack(side='right', padx=20, pady=20)

        if self.read_only:
             tk.Label(header, text="(מצב צפייה)", font=('Segoe UI', 10),
                bg=COLORS['primary'], fg='#f39c12').pack(side='left', padx=20)

        # --- קנבס גלילה ---
        content = tk.Frame(self.window, bg=COLORS['bg'])
        content.pack(fill='both', expand=True, padx=15, pady=15)

        canvas = tk.Canvas(content, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = tk.Scrollbar(content, orient="vertical", command=canvas.yview)

        self.cards_frame = tk.Frame(canvas, bg=COLORS['bg'])

        # יצירת חלון בתוך הקנבס
        canvas.create_window((0, 0), window=self.cards_frame, anchor='nw', width=730)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        self.cards_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))

        self._create_cards()

        # --- כפתורים למטה ---
        if not self.read_only:
            footer = tk.Frame(self.window, bg=COLORS['bg'])
            footer.pack(fill='x', pady=15, padx=20)

            tk.Button(footer, text="➕ הוסף קבוצה", font=('Segoe UI', 11, 'bold'),
                     bg=COLORS['success'], fg='white', relief='flat', cursor='hand2',
                     padx=20, pady=5, command=self._add_group).pack(side='right')

            tk.Button(footer, text="סגור", font=('Segoe UI', 11),
                     bg='white', fg=COLORS['text'], relief='flat', bd=1,
                     padx=20, pady=5, command=self.window.destroy).pack(side='left')
        else:
            tk.Button(self.window, text="סגור", command=self.window.destroy).pack(pady=10)

    def _create_cards(self):
        for widget in self.cards_frame.winfo_children():
            widget.destroy()

        if not self.groups_urls:
            tk.Label(self.cards_frame, text="אין קבוצות עדיין", bg=COLORS['bg'], fg='gray').pack(pady=50)
            return

        for idx in range(len(self.groups_urls)):
            self._create_card(idx)

    def _create_card(self, idx):
        name = self.groups_names[idx]
        url = self.groups_urls[idx]
        is_active = self.groups_active[idx]

        # 1. המסגרת הראשית (הכרטיס) - שיטת בנייה פשוטה יותר
        card = tk.Frame(self.cards_frame, bg=COLORS['card'],
                       highlightbackground=COLORS['card_border'],
                       highlightthickness=1,
                       bd=0)
        card.pack(fill='x', pady=5, padx=5, ipady=5) # ipady נותן קצת גובה פנימי

        # 2. פס סטטוס צבעוני (הכי ימני)
        status_color = COLORS['success'] if is_active else COLORS['warning']
        status_strip = tk.Frame(card, bg=status_color, width=6)
        status_strip.pack(side='right', fill='y', padx=(0,0)) # צמוד לימין

        # 3. אזור הטקסט (ימין)
        text_area = tk.Frame(card, bg=COLORS['card'])
        text_area.pack(side='right', fill='y', padx=15)

        name_lbl = tk.Label(text_area, text=name, font=('Segoe UI', 12, 'bold'),
                           bg=COLORS['card'], fg=COLORS['text'])
        name_lbl.pack(anchor='e')

        short_url = url[:50] + "..." if len(url) > 50 else url
        url_lbl = tk.Label(text_area, text=short_url, font=('Segoe UI', 9),
                          bg=COLORS['card'], fg=COLORS['text_light'], cursor="hand2")
        url_lbl.pack(anchor='e')
        url_lbl.bind("<Button-1>", lambda e: webbrowser.open(url))

        # 4. אזור הכפתורים (שמאל) - רק אם לא במצב צפייה
        if not self.read_only:
            btn_area = tk.Frame(card, bg=COLORS['card'])
            btn_area.pack(side='left', padx=15)

            # פונקציית עזר לכפתור
            def make_btn(txt, color, cmd):
                b = tk.Button(btn_area, text=txt, font=('Segoe UI', 10),
                             bg='white', fg=color,
                             relief='solid', bd=1,
                             cursor='hand2', width=5,
                             command=cmd)
                b.pack(side='left', padx=3)

                # אפקטים
                b.bind("<Enter>", lambda e: b.config(bg=color, fg='white'))
                b.bind("<Leave>", lambda e: b.config(bg='white', fg=color))
                return b

            # כפתור מחיקה
            make_btn("🗑", COLORS['danger'], lambda: self._delete_group(idx))

            # כפתור הפעלה/השהיה
            toggle_txt = "⏸" if is_active else "▶"
            toggle_col = COLORS['warning'] if is_active else COLORS['success']
            make_btn(toggle_txt, toggle_col, lambda: self._toggle_group(idx))

            # כפתור עריכה
            make_btn("✎", COLORS['accent'], lambda: self._edit_group(idx))

    # --- לוגיקה ---
    def _add_group(self):
        AddGroupDialog(self.window, self._on_group_added)

    def _edit_group(self, idx):
        EditGroupDialog(self.window, self.groups_names[idx], self.groups_urls[idx],
                       lambda n, u: self._on_group_edited(idx, n, u))

    def _toggle_group(self, idx):
        self.groups_active[idx] = not self.groups_active[idx]
        if self._save_groups(): self._create_cards()

    def _delete_group(self, idx):
        if messagebox.askyesno("מחיקה", "למחוק את הקבוצה?"):
            del self.groups_urls[idx]
            del self.groups_names[idx]
            del self.groups_active[idx]
            if self._save_groups(): self._create_cards()

    def _on_group_added(self, name, url):
        self.groups_names.append(name)
        self.groups_urls.append(url)
        self.groups_active.append(True)
        if self._save_groups(): self._create_cards()

    def _on_group_edited(self, idx, name, url):
        self.groups_names[idx] = name
        self.groups_urls[idx] = url
        if self._save_groups(): self._create_cards()


# --- חלונות עזר ---
class AddGroupDialog:
    def __init__(self, parent, callback):
        self.callback = callback
        self.window = tk.Toplevel(parent)
        self.window.title("הוספה")
        self.window.geometry("450x300")
        self.window.configure(bg='white')
        self._ui()
        self.window.transient(parent)
        self.window.grab_set()

    def _ui(self):
        tk.Label(self.window, text="שם הקבוצה:", bg='white').pack(anchor='e', padx=20, pady=(20,0))
        self.e_name = tk.Entry(self.window, font=('Segoe UI', 11), bg='#f0f0f0', relief='flat')
        self.e_name.pack(fill='x', padx=20, ipady=5)

        tk.Label(self.window, text="קישור (URL):", bg='white').pack(anchor='e', padx=20, pady=(15,0))
        self.e_url = tk.Entry(self.window, font=('Segoe UI', 11), bg='#f0f0f0', relief='flat')
        self.e_url.pack(fill='x', padx=20, ipady=5)

        tk.Button(self.window, text="שמור", bg=COLORS['success'], fg='white',
                 command=self._save, relief='flat', padx=20, pady=5).pack(pady=30)

    def _save(self):
        n, u = self.e_name.get().strip(), self.e_url.get().strip()
        if n and u and "facebook" in u:
            self.callback(n, u)
            self.window.destroy()
        else:
            messagebox.showerror("שגיאה", "נא למלא פרטים תקינים")

class EditGroupDialog(AddGroupDialog):
    def __init__(self, parent, name, url, callback):
        self.init_name = name
        self.init_url = url
        super().__init__(parent, callback)

    def _ui(self):
        super()._ui()
        self.e_name.insert(0, self.init_name)
        self.e_url.insert(0, self.init_url)
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class ListingCardWidget(QFrame):
    """
    וידג'ט המייצג כרטיסייה בודדת של מודעת נדל"ן.
    """

    def __init__(self, location, price, rooms, time_found, parent=None):
        super().__init__(parent)

        # --- הגדרות עיצוב כלליות לכרטיסייה ---
        self.setObjectName("ListingCard")
        self.setStyleSheet("""
            #ListingCard {
                background-color: #ffffff;
                border-radius: 10px;
                border: 1px solid #e0e0e0;
            }
            QLabel {
                color: #333333;
            }
        """)
        # הוספת צל עדין (אופציונלי, דורש קצת יותר קוד, נשאיר פשוט כרגע)

        # --- פריסה ראשית (אנכית) ---
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        main_layout.setContentsMargins(15, 15, 15, 15)  # מרווחים פנימיים
        main_layout.setSpacing(10)  # מרווח בין שורות

        # --- שורה 1: מיקום ושעה ---
        header_layout = QHBoxLayout()

        # מיקום (מודגש)
        location_label = QLabel(f"📍 {location}")
        location_font = QFont()
        location_font.setBold(True)
        location_font.setPointSize(11)
        location_label.setFont(location_font)
        header_layout.addWidget(location_label)

        header_layout.addStretch()  # דוחף את השעה שמאלה

        # שעה
        time_label = QLabel(time_found)
        time_label.setStyleSheet("color: #888888; font-size: 10pt;")
        header_layout.addWidget(time_label)

        main_layout.addLayout(header_layout)

        # --- שורה 2: מחיר (גדול וירוק) ---
        price_label = QLabel(f"₪{price}")
        price_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        price_font = QFont()
        price_font.setBold(True)
        price_font.setPointSize(18)
        price_label.setFont(price_font)
        # צבע ירוק למחיר
        price_label.setStyleSheet("color: #27ae60;")
        main_layout.addWidget(price_label)

        # --- שורה 3: פרטים נוספים (חדרים וכו') ---
        details_layout = QHBoxLayout()

        # חדרים
        rooms_label = QLabel(f"🛏️ {rooms} חדרים")
        rooms_label.setStyleSheet("background-color: #f0f2f5; padding: 5px; border-radius: 5px;")
        details_layout.addWidget(rooms_label)

        details_layout.addStretch()  # מרווח

        # אפשר להוסיף פה עוד פרטים בעתיד (קומה, מ"ר)
        # floor_label = QLabel("קומה 2")
        # details_layout.addWidget(floor_label)

        main_layout.addLayout(details_layout)

        # הגדרת גודל קבוע לכרטיסייה כדי שייראו אחידות
        self.setFixedSize(280, 160)
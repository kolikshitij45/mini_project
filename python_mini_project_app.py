# code of python mini project: student id card generator with qr
import os, sys, sqlite3, tempfile, hashlib, re, requests, base64
from PySide6 import QtCore, QtGui, QtWidgets
from PIL import Image, ImageDraw, ImageFont
import qrcode
from reportlab.pdfgen import canvas

# -------- CONFIG --------
DB_PATH = "eduid_maker.db"
APP_TITLE = "Welcome to EduID Maker!"
ACCENT_COLOR = "#2f9e44"
DASHBOARD_BG = "#d7f9b1"
LOGIN_BG = "#1c1c1c"
ID_SIZE = (630, 1000)

# -------- DATABASE --------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        email TEXT,
        password TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS ids(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        student_id TEXT,
        course TEXT,
        year TEXT,
        department TEXT,
        phone TEXT,
        email TEXT,
        pdf_path TEXT)""")
    conn.commit()
    conn.close()

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def validate_email(e):
    return bool(re.match(r"[^@]+@[^@]+\.[^@]+", e))

# -------- IMAGE UTILS --------
def make_rounded(img: Image.Image, size):
    img = img.convert("RGBA").resize(size, Image.Resampling.LANCZOS)
    mask = Image.new("L", size, 0)
    d = ImageDraw.Draw(mask)
    d.ellipse((0, 0, size[0], size[1]), fill=255)
    img.putalpha(mask)
    return img

def make_qr(text, size=150):
    qr = qrcode.make(text).convert("RGBA").resize((size, size))
    return qr

# -------- UPLOAD TO IMGBB --------
def upload_to_imgbb(local_path):
    api_key = "f59c4fbcf150b55e7f0d732d71d97a38"  # Replace with your actual key
    try:
        with open(local_path, "rb") as f:
            img_b64 = base64.b64encode(f.read())
        resp = requests.post(
            "https://api.imgbb.com/1/upload",
            data={"key": api_key, "image": img_b64}
        )
        if resp.status_code == 200:
            j = resp.json()
            return j["data"]["url"]
        else:
            print("Upload failed:", resp.text)
            return None
    except Exception as e:
        print("Upload error:", e)
        return None

# -------- ID GENERATION --------
def generate_id(data, bg_path=None, logo_path=None, photo_path=None):
    W, H = ID_SIZE
    if bg_path and os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA").resize((W, H))
    else:
        bg = Image.new("RGBA", (W, H), "white")

    d = ImageDraw.Draw(bg)
    try:
        f_title = ImageFont.truetype("arialbd.ttf", 48)
        f_name = ImageFont.truetype("arialbd.ttf", 40)
        f_info = ImageFont.truetype("arial.ttf", 26)
    except:
        f_title = f_name = f_info = ImageFont.load_default()

    # Header
    text = "STUDENT"
    w_text = d.textlength(text, font=f_title)
    d.text(((W - w_text)//2, 40), text, font=f_title, fill="black")

    # Logo
    if logo_path and os.path.exists(logo_path):
        logo = make_rounded(Image.open(logo_path), (120, 120))
        bg.paste(logo, (25, 25), logo)

    # Photo
    y_photo = 150
    if photo_path and os.path.exists(photo_path):
        photo = make_rounded(Image.open(photo_path), (250, 300))
        bg.paste(photo, ((W - 250)//2, y_photo), photo)

    # Student Name
    y_name = y_photo + 320
    name = data.get("name", "")
    w_name = d.textlength(name, font=f_name)
    d.text(((W - w_name)//2, y_name), name, font=f_name, fill="black")

    # Info block 
    y_info = y_name + 90
    for label, val in [
        ("ID", data.get("student_id")),
        ("Course", data.get("course")),
        ("Year", data.get("year")),
        ("Department", data.get("department")),
        ("Phone", data.get("phone")),
        ("Email", data.get("email")),
    ]:
        d.text((50, y_info), f"{label}: {val or ''}", font=f_info, fill="black")
        y_info += 45

    # Save temporary ID image locally
    os.makedirs("generated_cards", exist_ok=True)
    local_name = f"{data.get('student_id','temp')}_card.png"
    local_path = os.path.abspath(os.path.join("generated_cards", local_name))
    bg.save(local_path)

    # Upload to imgbb
    link = upload_to_imgbb(local_path)
    if not link:
        link = f"file:///{local_path.replace(os.sep, '/')}"

    qr = make_qr(link, size=180)
    bg.paste(qr, (W - qr.width - 40, y_name + 110), qr)

    return bg.convert("RGB")

# -------- LOGIN & SIGNUP --------
class Login(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setStyleSheet(f"background-color:{LOGIN_BG}; color:white;")
        v = QtWidgets.QVBoxLayout(self)
        v.setAlignment(QtCore.Qt.AlignCenter)

        title = QtWidgets.QLabel(APP_TITLE)
        title.setAlignment(QtCore.Qt.AlignCenter)
        title.setStyleSheet(f"font-size:50px; color:{ACCENT_COLOR}; margin-bottom:40px;")
        v.addWidget(title)

        box = QtWidgets.QFrame()
        box.setFixedSize(400, 280)
        box.setStyleSheet("background-color:#2c2c2c; border-radius:10px;")
        form = QtWidgets.QVBoxLayout(box)

        self.user = QtWidgets.QLineEdit(); self.user.setPlaceholderText("Username")
        self.passw = QtWidgets.QLineEdit(); self.passw.setPlaceholderText("Password")
        self.passw.setEchoMode(QtWidgets.QLineEdit.Password)
        for e in (self.user, self.passw):
            e.setFixedHeight(40)
            e.setStyleSheet("font-size:18px; margin:8px;")
            form.addWidget(e)

        login_btn = QtWidgets.QPushButton("Login")
        signup_btn = QtWidgets.QPushButton("Signup")
        for b in (login_btn, signup_btn):
            b.setFixedHeight(40)
            b.setStyleSheet(f"background-color:{ACCENT_COLOR}; color:white; font-size:18px; border-radius:8px; margin:6px;")
            form.addWidget(b)

        login_btn.clicked.connect(self.login)
        signup_btn.clicked.connect(self.signup)
        v.addWidget(box)

    def login(self):
        u, p = self.user.text().strip(), self.passw.text().strip()
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT password FROM users WHERE username=?", (u,))
        row = cur.fetchone(); conn.close()
        if row and row[0] == hash_password(p):
            self.dash = Dashboard(); self.dash.show(); self.close()
        else:
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid credentials!")

    def signup(self):
        self.su = Signup(); self.su.show(); self.close()

class Signup(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Signup")
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.setStyleSheet(f"background-color:{LOGIN_BG}; color:white;")
        v = QtWidgets.QVBoxLayout(self); v.setAlignment(QtCore.Qt.AlignCenter)

        title = QtWidgets.QLabel("Create Account")
        title.setStyleSheet(f"font-size:48px; color:{ACCENT_COLOR}; margin-bottom:40px;")
        title.setAlignment(QtCore.Qt.AlignCenter)
        v.addWidget(title)

        box = QtWidgets.QFrame(); box.setFixedSize(420, 360)
        box.setStyleSheet("background-color:#2c2c2c; border-radius:10px;")
        f = QtWidgets.QVBoxLayout(box)
        self.u = QtWidgets.QLineEdit(); self.u.setPlaceholderText("Username")
        self.e = QtWidgets.QLineEdit(); self.e.setPlaceholderText("Email")
        self.p = QtWidgets.QLineEdit(); self.p.setPlaceholderText("Password")
        self.p.setEchoMode(QtWidgets.QLineEdit.Password)
        for w in (self.u, self.e, self.p):
            w.setFixedHeight(40); w.setStyleSheet("font-size:18px; margin:8px;")
            f.addWidget(w)

        b = QtWidgets.QPushButton("Create Account")
        b.setStyleSheet(f"background-color:{ACCENT_COLOR}; color:white; font-size:18px; border-radius:8px; margin-top:12px;")
        b.clicked.connect(self.create)
        f.addWidget(b)
        v.addWidget(box)

    def create(self):
        u, e, p = self.u.text(), self.e.text(), self.p.text()
        if not u or not e or not p:
            QtWidgets.QMessageBox.warning(self, "Error", "All fields required")
            return
        if not validate_email(e):
            QtWidgets.QMessageBox.warning(self, "Error", "Invalid email")
            return
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        try:
            cur.execute("INSERT INTO users(username,email,password) VALUES(?,?,?)", (u,e,hash_password(p)))
            conn.commit(); QtWidgets.QMessageBox.information(self, "Success", "Account Created!")
            self.l = Login(); self.l.show(); self.close()
        except sqlite3.IntegrityError:
            QtWidgets.QMessageBox.warning(self, "Error", "Username already exists")
        conn.close()

# -------- DASHBOARD --------
class Dashboard(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.setWindowState(QtCore.Qt.WindowMaximized)
        self.bg = self.logo = self.photo = None
        self.init_ui()

    def init_ui(self):
        h = QtWidgets.QHBoxLayout(self)
        side = QtWidgets.QFrame(); side.setFixedWidth(230)
        side.setStyleSheet(f"background-color:{LOGIN_BG}; color:white;")
        sv = QtWidgets.QVBoxLayout(side); sv.setAlignment(QtCore.Qt.AlignTop)
        lbl = QtWidgets.QLabel(APP_TITLE)
        lbl.setAlignment(QtCore.Qt.AlignCenter)
        lbl.setStyleSheet(f"font-size:26px; color:{ACCENT_COLOR}; margin-top:20px; margin-bottom:30px;")
        sv.addWidget(lbl)
        for text, fn in [
            ("Generate ID", lambda: self.stack.setCurrentIndex(0)),
            ("View Records", lambda: (self.stack.setCurrentIndex(1), self.load_records())),
            ("Logout", self.logout)
        ]:
            b = QtWidgets.QPushButton(text)
            b.setFixedHeight(46)
            b.setStyleSheet(f"background-color:{ACCENT_COLOR}; color:white; font-size:18px; border-radius:8px; margin:8px;")
            b.clicked.connect(fn)
            sv.addWidget(b)
        h.addWidget(side)

        # Stack
        self.stack = QtWidgets.QStackedWidget()
        h.addWidget(self.stack, 1)
        self.page_gen = self.make_generate_page()
        self.page_rec = self.make_records_page()
        self.stack.addWidget(self.page_gen)
        self.stack.addWidget(self.page_rec)

    # ----------------------- Generate Page -----------------------
    def make_generate_page(self):
        page = QtWidgets.QWidget(); page.setStyleSheet(f"background-color:{DASHBOARD_BG};")
        layout = QtWidgets.QHBoxLayout(page)
        left = QtWidgets.QFrame(); l = QtWidgets.QVBoxLayout(left); l.setAlignment(QtCore.Qt.AlignTop)

        def field(ph):
            e = QtWidgets.QLineEdit(); e.setPlaceholderText(ph)
            e.setFixedHeight(48); e.setFixedWidth(400)
            e.setStyleSheet("font-size:18px; margin:6px;")
            return e

        self.name,self.sid,self.course,self.year,self.phone,self.email = [field(x) for x in
            ("Name","Student ID","Course","Year","Phone","Email")]
        self.dept = QtWidgets.QComboBox()
        self.dept.addItems(["Computer","IT","ECS","EXTC","Automobile","Mechanical","Commerce","Science","Arts"])
        self.dept.setFixedHeight(48); self.dept.setFixedWidth(400)
        self.dept.setStyleSheet("font-size:18px; margin:6px;")
        for w in (self.name,self.sid,self.course,self.year,self.dept,self.phone,self.email): l.addWidget(w)

        for txt, attr in [("Load Photo","photo"),("Load Logo","logo"),("Load Background","bg")]:
            b = QtWidgets.QPushButton(txt)
            b.setFixedHeight(44)
            b.setStyleSheet("background:white; color:black; font-size:17px; border-radius:6px; margin:6px;")
            b.clicked.connect(lambda _, a=attr: self.load_image(a))
            l.addWidget(b)

        f = QtWidgets.QFrame(); fl = QtWidgets.QVBoxLayout(f)
        for txt, fn in [("Generate Preview", self.generate_preview),("Save in Records", self.save_record),("Refresh", self.refresh),("Save as PDF", self.save_pdf)]:
            b = QtWidgets.QPushButton(txt)
            b.setFixedHeight(46)
            b.setStyleSheet(f"background-color:{ACCENT_COLOR}; color:white; font-size:17px; border-radius:6px; margin:4px;")
            b.clicked.connect(fn); fl.addWidget(b)
        l.addWidget(f)
        layout.addWidget(left)

        right = QtWidgets.QFrame(); rv = QtWidgets.QVBoxLayout(right); rv.setAlignment(QtCore.Qt.AlignCenter)
        self.preview = QtWidgets.QLabel("Preview will appear here\n(Click Generate Preview)")
        self.preview.setFixedSize(450, 650)
        self.preview.setStyleSheet("background:white; border:2px dashed gray; font-size:16px; text-align:center;")
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        rv.addWidget(self.preview)
        layout.addWidget(right, 1)
        return page

    def load_image(self, kind):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, f"Select {kind}", "", "Image Files (*.png *.jpg *.jpeg)")
        if path:
            setattr(self, kind, path)
            QtWidgets.QMessageBox.information(self, "Loaded", f"{kind.capitalize()} loaded successfully!")

    def collect(self):
        return {
            "name": self.name.text(),
            "student_id": self.sid.text(),
            "course": self.course.text(),
            "year": self.year.text(),
            "department": self.dept.currentText(),
            "phone": self.phone.text(),
            "email": self.email.text()
        }

    def generate_preview(self):
        data = self.collect()
        if not data["name"] or not data["student_id"]:
            QtWidgets.QMessageBox.warning(self, "Error", "Name and Student ID required!")
            return
        img = generate_id(data, self.bg, self.logo, self.photo)
        tmp = os.path.join(tempfile.gettempdir(), "preview_card.png")
        img.save(tmp)
        pix = QtGui.QPixmap(tmp)
        self.preview.setPixmap(pix.scaled(self.preview.size(), QtCore.Qt.KeepAspectRatio, QtCore.Qt.SmoothTransformation))

    def save_record(self):
        data = self.collect()
        if not data["name"] or not data["student_id"]:
            QtWidgets.QMessageBox.warning(self, "Error", "Enter Name and Student ID first!")
            return
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("""INSERT INTO ids(name,student_id,course,year,department,phone,email,pdf_path)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (data["name"],data["student_id"],data["course"],data["year"],
                     data["department"],data["phone"],data["email"],""))
        conn.commit(); conn.close()
        QtWidgets.QMessageBox.information(self, "Saved", "Record saved successfully!")

    def refresh(self):
        for w in (self.name,self.sid,self.course,self.year,self.phone,self.email): w.clear()
        self.dept.setCurrentIndex(0)
        self.bg=self.logo=self.photo=None
        self.preview.clear()
        self.preview.setText("Preview will appear here\n(Click Generate Preview)")

    def save_pdf(self):
        data = self.collect()
        if not data["name"] or not data["student_id"]:
            QtWidgets.QMessageBox.warning(self,"Error","Enter Name and ID first!")
            return
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Save PDF","","PDF Files (*.pdf)")
        if not path: return
        img = generate_id(data,self.bg,self.logo,self.photo)
        temp = tempfile.NamedTemporaryFile(delete=False,suffix=".png")
        img.save(temp.name)
        c = canvas.Canvas(path, pagesize=(ID_SIZE[0],ID_SIZE[1]))
        c.drawImage(temp.name,0,0,width=ID_SIZE[0],height=ID_SIZE[1])
        c.save(); os.remove(temp.name)
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("""INSERT INTO ids(name,student_id,course,year,department,phone,email,pdf_path)
                       VALUES(?,?,?,?,?,?,?,?)""",
                    (data["name"],data["student_id"],data["course"],data["year"],
                     data["department"],data["phone"],data["email"],path))
        conn.commit(); conn.close()
        QtWidgets.QMessageBox.information(self,"Saved","PDF saved successfully!")

    # ----------------------- Records Page -----------------------
    def make_records_page(self):
        page = QtWidgets.QWidget(); page.setStyleSheet(f"background-color:{DASHBOARD_BG};")
        layout = QtWidgets.QVBoxLayout(page)

        # Top Buttons
        btn_frame = QtWidgets.QFrame(); btn_layout = QtWidgets.QHBoxLayout(btn_frame)
        self.del_btn = QtWidgets.QPushButton("Delete Record")
        self.del_btn.setStyleSheet(f"background-color:red; color:white; font-size:16px; border-radius:6px;")
        self.del_btn.clicked.connect(self.delete_record)

        self.pdf_btn = QtWidgets.QPushButton("Export as PDF")
        self.pdf_btn.setStyleSheet(f"background-color:{ACCENT_COLOR}; color:white; font-size:16px; border-radius:6px;")
        self.pdf_btn.clicked.connect(self.export_pdf)

        self.search_btn = QtWidgets.QPushButton("Search by Student ID")
        self.search_btn.setStyleSheet(f"background-color:blue; color:white; font-size:16px; border-radius:6px;")
        self.search_btn.clicked.connect(self.search_record)

        # ✅ New Refresh Button
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.setStyleSheet(f"background-color:orange; color:white; font-size:16px; border-radius:6px;")
        self.refresh_btn.clicked.connect(lambda: self.load_records())

        # Add all buttons to layout
        btn_layout.addWidget(self.del_btn)
        btn_layout.addWidget(self.pdf_btn)
        btn_layout.addWidget(self.search_btn)
        btn_layout.addWidget(self.refresh_btn)

        layout.addWidget(btn_frame)

        self.table = QtWidgets.QTableWidget(); layout.addWidget(self.table)
        return page

    def load_records(self, filter_id=None):
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        if filter_id:
            cur.execute("SELECT id,name,student_id,course,year,department,phone,email,pdf_path FROM ids WHERE student_id=?", (filter_id,))
        else:
            cur.execute("SELECT id,name,student_id,course,year,department,phone,email,pdf_path FROM ids")
        rows = cur.fetchall(); conn.close()
        self.table.setRowCount(len(rows)); self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels(["ID","Name","Student ID","Course","Year","Dept","Phone","Email","PDF Path"])
        for i,r in enumerate(rows):
            for j,val in enumerate(r):
                self.table.setItem(i,j,QtWidgets.QTableWidgetItem(str(val)))
        self.table.resizeColumnsToContents()
        if filter_id and not rows:
            QtWidgets.QMessageBox.information(self, "Not Found", "Student not found!")

    def delete_record(self):
        sel = self.table.currentRow()
        if sel < 0: return
        student_id = self.table.item(sel,2).text()
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("DELETE FROM ids WHERE student_id=?", (student_id,))
        conn.commit(); conn.close()
        self.load_records()
        QtWidgets.QMessageBox.information(self,"Deleted","Record deleted successfully!")

    def export_pdf(self):
        sel = self.table.currentRow()
        if sel < 0: return
        student_id = self.table.item(sel,2).text()
        conn = sqlite3.connect(DB_PATH); cur = conn.cursor()
        cur.execute("SELECT name,student_id,course,year,department,phone,email FROM ids WHERE student_id=?", (student_id,))
        row = cur.fetchone(); conn.close()
        if row:
            data = {"name":row[0],"student_id":row[1],"course":row[2],"year":row[3],"department":row[4],"phone":row[5],"email":row[6]}
            path, _ = QtWidgets.QFileDialog.getSaveFileName(self,"Export PDF","","PDF Files (*.pdf)")
            if not path: return
            img = generate_id(data,self.bg,self.logo,self.photo)
            temp = tempfile.NamedTemporaryFile(delete=False,suffix=".png")
            img.save(temp.name)
            c = canvas.Canvas(path, pagesize=(ID_SIZE[0],ID_SIZE[1]))
            c.drawImage(temp.name,0,0,width=ID_SIZE[0],height=ID_SIZE[1])
            c.save(); os.remove(temp.name)
            QtWidgets.QMessageBox.information(self,"Saved","PDF exported successfully!")

    def search_record(self):
        text, ok = QtWidgets.QInputDialog.getText(self,"Search","Enter Student ID:")
        if ok and text.strip():
            self.load_records(filter_id=text.strip())

    def logout(self):
        self.l = Login(); self.l.show(); self.close()

# -------- MAIN --------
if __name__ == "__main__":
    init_db()
    app = QtWidgets.QApplication(sys.argv)
    w = Login(); w.show()
    sys.exit(app.exec())

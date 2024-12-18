import os
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'secret_key'

<<<<<<< HEAD
# SQLite Veritabanı bağlantısı
DATABASE = 'database.db'

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

# Veritabanı tablolarını oluşturma
with get_db_connection() as conn:
    conn.execute('''CREATE TABLE IF NOT EXISTS users (
        email TEXT PRIMARY KEY,
        password TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        organization TEXT,
        department TEXT,
        work_phone TEXT,
        gsm TEXT,
        profile_photo TEXT
    )''')
=======
# Firebase yapılandırması
if os.path.exists("firebase_key.json"):
    # firebase_key.json kullanımı
    cred = credentials.Certificate("firebase_key.json")
else:
    raise FileNotFoundError("firebase_key.json dosyası bulunamadı. Lütfen dosyayı doğru yere yerleştirin.")

firebase_admin.initialize_app(cred)
db = firestore.client()
>>>>>>> a060b080e921c5f036f995ae6893a7687edffca7

# Kullanıcı e-posta gönderimi
def send_email(to_email):
    sender_email = "meadeneme00@gmail.com"  # Zoho e-posta adresiniz
    password = "rX7j/v/fg@R98*/"  # Zoho Mail şifreniz

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = "Kayıt Başarılı"

    body = "Kayıt işleminiz başarılı bir şekilde tamamlandı."
    msg.attach(MIMEText(body, "plain"))

    try:
        # Zoho SMTP sunucusuna bağlanma
        server = smtplib.SMTP("smtp.zoho.com", 587)
        server.starttls()  # Güvenli bağlantıyı başlat
        server.login(sender_email, password)  # Zoho kimlik doğrulama
        server.sendmail(sender_email, to_email, msg.as_string())
        print("E-posta başarıyla gönderildi.")
    except Exception as e:
        print(f"E-posta gönderilirken bir hata oluştu: {e}")
    finally:
        server.quit()

# Ana rota
@app.route('/')
def index():
    return render_template('index.html')

# Kayıt olma
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        user_data = {
            "email": email,
            "password": hashed_password,
            "first_name": None,
            "last_name": None,
            "organization": None,
            "department": None,
            "work_phone": None,
            "gsm": None,
            "profile_photo": None,
        }

        try:
            with get_db_connection() as conn:
                conn.execute('''INSERT INTO users (email, password, first_name, last_name, organization, department, work_phone, gsm, profile_photo)
                                VALUES (:email, :password, :first_name, :last_name, :organization, :department, :work_phone, :gsm, :profile_photo)''',
                             user_data)

            send_email(email)
            flash("Kayıt başarılı! Lütfen giriş yapın.", "success")
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash("Bu e-posta adresi zaten kayıtlı.", "danger")
        except Exception as e:
            print(f"Veritabanı kaydı sırasında hata: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")

    return render_template('register.html')

# Giriş yapma
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            with get_db_connection() as conn:
                user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

            if user and check_password_hash(user['password'], password):
                session['user_id'] = email
                flash("Giriş başarılı!", "success")
                return redirect(url_for('hello'))
            else:
                flash("Geçersiz giriş bilgileri.", "danger")
        except Exception as e:
            print(f"Veritabanı sorgusu sırasında hata: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")

    return render_template('login.html')

# Eksik bilgiler
@app.route('/hello', methods=['GET', 'POST'])
def hello():
    if 'user_id' not in session:
        flash("Bu sayfaya erişmek için lütfen giriş yapın.", "danger")
        return redirect(url_for('login'))

    email = session['user_id']

    try:
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()

        if request.method == 'POST':
            updated_data = {
                "first_name": request.form.get('first_name'),
                "last_name": request.form.get('last_name'),
                "organization": request.form.get('organization'),
                "department": request.form.get('department'),
                "work_phone": request.form.get('work_phone'),
                "gsm": request.form.get('gsm'),
                "email": email
            }
            with get_db_connection() as conn:
                conn.execute('''UPDATE users SET first_name = :first_name, last_name = :last_name, organization = :organization, 
                                department = :department, work_phone = :work_phone, gsm = :gsm WHERE email = :email''',
                             updated_data)
            flash("Bilgileriniz başarıyla güncellendi.", "success")
    except Exception as e:
        print(f"Veritabanı güncellemesi sırasında hata: {e}")
        flash("Bilgiler güncellenirken bir hata oluştu.", "danger")

    return render_template('hello.html', user=user)

# Çıkış yapma
@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

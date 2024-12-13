import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import firebase_admin
from firebase_admin import credentials, firestore
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'secret_key'

# Firebase yapılandırması
cred = credentials.Certificate("firebase_key.json")  # Firebase hizmet hesabı dosyanız
firebase_admin.initialize_app(cred)
db = firestore.client()

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
            # Firebase'de kullanıcı kaydı oluştur
            user_ref = db.collection('users').document(email)
            user_ref.set(user_data)

            send_email(email)
            flash("Kayıt başarılı! Lütfen giriş yapın.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Firebase kaydı sırasında hata: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")

    return render_template('register.html')

# Giriş yapma
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            user_ref = db.collection('users').document(email)
            user = user_ref.get()

            if user.exists:
                user_data = user.to_dict()
                if check_password_hash(user_data['password'], password):
                    session['user_id'] = email
                    flash("Giriş başarılı!", "success")
                    return redirect(url_for('hello'))
                else:
                    flash("Geçersiz giriş bilgileri.", "danger")
            else:
                flash("E-posta adresi bulunamadı.", "danger")
        except Exception as e:
            print(f"Firebase sorgusu sırasında hata: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")

    return render_template('login.html')

# Eksik bilgiler
@app.route('/hello', methods=['GET', 'POST'])
def hello():
    if 'user_id' not in session:
        flash("Bu sayfaya erişmek için lütfen giriş yapın.", "danger")
        return redirect(url_for('login'))

    # Firebase'den kullanıcı bilgilerini çekme
    email = session['user_id']
    user_ref = db.collection('users').document(email)
    user = user_ref.get().to_dict()

    if request.method == 'POST':
        # Eksik bilgileri kaydet
        updated_data = {
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
            "organization": request.form.get('organization'),
            "department": request.form.get('department'),
            "work_phone": request.form.get('work_phone'),
            "gsm": request.form.get('gsm'),
        }
        try:
            user_ref.update(updated_data)
            flash("Bilgileriniz başarıyla güncellendi.", "success")
            user.update(updated_data)
        except Exception as e:
            print(f"Firebase güncellemesi sırasında hata: {e}")
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
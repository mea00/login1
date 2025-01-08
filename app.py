import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import pg8000
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore

# .env dosyasını yükle
load_dotenv()

app = Flask(__name__)
app.secret_key = 'secret_key'

# PostgreSQL bağlantı ayarları
DATABASE_URL = os.getenv("DATABASE_URL")

def get_db_connection():
    try:
        conn = pg8000.connect(DATABASE_URL)
        return conn
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

# Firebase yapılandırması
firebase_config = {
    "type": "service_account",
    "project_id": os.getenv("FIREBASE_PROJECT_ID"),
    "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
    "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace("\\n", "\n"),
    "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
    "client_id": os.getenv("FIREBASE_CLIENT_ID"),
    "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
    "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
    "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_CERT_URL"),
    "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_CERT_URL"),
}

cred = credentials.Certificate(firebase_config)
firebase_admin.initialize_app(cred)
firestore_db = firestore.client()

# SendGrid üzerinden e-posta gönderimi
def send_email(to_email, subject, body):
    sender_email = "meadeneme00@gmail.com"
    sg_api_key = os.getenv("SENDGRID_API_KEY")

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        print("SMTP bağlantısı kuruluyor...")
        server = smtplib.SMTP("smtp.sendgrid.net", 587)
        server.starttls()
        print("SendGrid'e giriş yapılıyor...")
        server.login("apikey", sg_api_key)
        print("E-posta gönderiliyor...")
        server.sendmail(sender_email, to_email, msg.as_string())
        print(f"E-posta başarıyla gönderildi: {to_email}")
    except Exception as e:
        print(f"E-posta gönderim hatası: {e}")
    finally:
        server.quit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        user_data = {
            "email": email,
            "password": hashed_password,
            "is_active": False
        }

        try:
            # Firebase Firestore'a kullanıcı kaydet
            firestore_db.collection("users").add(user_data)

            # E-posta doğrulama bağlantısı gönder
            verification_url = f"{request.url_root}verify?email={email}"
            subject = "Hesap Aktivasyonu için Doğrulama Linkiniz"
            body = f"""
            
            Lütfen hesabınızı aktif hale getirmek için aşağıdaki bağlantıya tıklayın:
            {verification_url}

            Teşekkürler
            """
            send_email(email, subject, body)
            flash("Kayıt başarılı! Lütfen e-posta adresinize gelen bağlantıyı doğrulayın.", "success")
            return redirect(url_for('login'))
        except Exception as e:
            print(f"Kayıt hatası: {e}")
            flash("Kayıt sırasında bir hata oluştu.", "danger")
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        try:
            # Firestore'dan kullanıcıyı al
            users = firestore_db.collection("users").where("email", "==", email).stream()
            user = next(users, None)

            if user:
                user_data = user.to_dict()
                if check_password_hash(user_data['password'], password):
                    if not user_data['is_active']:
                        flash("Hesabınız aktif değil. Lütfen e-posta adresinize gelen doğrulama bağlantısını tıklayın.", "danger")
                        return redirect(url_for('index'))

                    session['user_id'] = email
                    flash("Giriş başarılı!", "success")
                    return redirect(url_for('hello'))
                else:
                    flash("Geçersiz giriş bilgileri.", "danger")
            else:
                flash("Kullanıcı bulunamadı.", "danger")
        except Exception as e:
            print(f"Giriş hatası: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        try:
            # Firestore'dan kullanıcıyı al
            users = firestore_db.collection("users").where("email", "==", email).stream()
            user = next(users, None)

            if user:
                reset_url = f"http://127.0.0.1:5000/reset-password?email={email}"
                subject = "Şifre Sıfırlama Talebi"
                body = f"""
                Merhaba,

                Şifrenizi sıfırlamak için aşağıdaki bağlantıya tıklayın:
                {reset_url}

                Eğer bu talebi siz yapmadıysanız, lütfen bu e-postayı dikkate almayın.

                Teşekkürler,
                """
                send_email(email, subject, body)
                flash("Şifre sıfırlama bağlantısı e-posta adresinize gönderildi.", "success")
            else:
                flash("Bu e-posta adresi sistemde kayıtlı değil.", "danger")
        except Exception as e:
            print(f"Şifre sıfırlama hatası: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")
    return render_template('forgot_password.html')

@app.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    email = request.args.get('email')
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        try:
            # Firestore'da şifreyi güncelle
            users = firestore_db.collection("users").where("email", "==", email).stream()
            user = next(users, None)

            if user:
                user.reference.update({"password": hashed_password})
                flash("Şifreniz başarıyla sıfırlandı. Lütfen giriş yapın.", "success")
                return redirect(url_for('login'))
            else:
                flash("Kullanıcı bulunamadı.", "danger")
        except Exception as e:
            print(f"Şifre sıfırlama sırasında hata: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")
    return render_template('reset_password.html', email=email)

@app.route('/hello', methods=['GET', 'POST'])
def hello():
    if 'user_id' not in session:
        flash("Bu sayfaya erişmek için lütfen giriş yapın.", "danger")
        return redirect(url_for('login'))

    email = session['user_id']

    try:
        # Firestore'dan kullanıcıyı al
        users = firestore_db.collection("users").where("email", "==", email).stream()
        user = next(users, None)

        if user:
            user_data = user.to_dict()

            if request.method == 'POST':
                updated_data = {
                    "first_name": request.form.get('first_name'),
                    "last_name": request.form.get('last_name'),
                    "profile_photo": request.form.get('profile_photo'),
                }
                user.reference.update(updated_data)
                flash("Bilgileriniz başarıyla güncellendi.", "success")
    except Exception as e:
        print(f"Bilgi güncelleme hatası: {e}")
        flash("Bilgiler güncellenirken bir hata oluştu.", "danger")

    return render_template('hello.html', user=user_data)

@app.route('/verify', methods=['GET'])
def verify():
    email = request.args.get('email')

    try:
        # Firestore'da kullanıcıyı aktif hale getir
        users = firestore_db.collection("users").where("email", "==", email).stream()
        user = next(users, None)

        if user:
            user.reference.update({"is_active": True})
            flash("E-posta doğrulama başarılı! Artık giriş yapabilirsiniz.", "success")
            return redirect(url_for('login'))
        else:
            flash("Kullanıcı bulunamadı.", "danger")
    except Exception as e:
        print(f"Doğrulama hatası: {e}")
        flash("Doğrulama sırasında bir hata oluştu.", "danger")
    return redirect(url_for('index'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    flash("Başarıyla çıkış yaptınız.", "success")
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)

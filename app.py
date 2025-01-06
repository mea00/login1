import os
from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2
from psycopg2.extras import RealDictCursor
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = Flask(__name__)
app.secret_key = 'secret_key'

# PostgreSQL bağlantı ayarları
DATABASE_URL = "postgresql://postgres:wrAeHQzqeeTpoDSauXvWyWnfOTxCqnYt@monorail.proxy.rlwy.net:47382/railway"

def get_db_connection():
    try:
        conn = psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)
        return conn
    except Exception as e:
        print(f"Veritabanı bağlantı hatası: {e}")
        return None

# SendGrid üzerinden e-posta gönderimi
def send_email(to_email, subject, body):
    sender_email = "meadeneme00@gmail.com"  # SendGrid'de doğrulanmış e-posta adresiniz
    sg_username = "cw1S8I4nTd6LeMM-KnkikA"  # SendGrid kullanıcı adı
    sg_api_key = "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"  # SendGrid API anahtarı

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        server = smtplib.SMTP("smtp.sendgrid.net", 587)
        server.starttls()
        server.login(sg_username, sg_api_key)
        server.sendmail(sender_email, to_email, msg.as_string())
        print(f"E-posta başarıyla gönderildi: {to_email}")
    except Exception as e:
        print(f"E-posta gönderilirken bir hata oluştu: {e}")
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

        user_data = (email, hashed_password, None, None, None, False)

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT * FROM users WHERE email = %s', (email,))
                if cur.fetchone():
                    flash("Bu e-posta adresi zaten kayıtlı.", "danger")
                    return redirect(url_for('register'))

                cur.execute('''INSERT INTO users (email, password, first_name, last_name, profile_photo, is_active)
                               VALUES (%s, %s, %s, %s, %s, %s)''', user_data)
                conn.commit()

            verification_url = f"http://127.0.0.1:5000/verify?email={email}"
            subject = "Hesap Aktivasyonu için Doğrulama Linkiniz"
            body = f"""
            Merhaba,

            Lütfen hesabınızı aktif hale getirmek için aşağıdaki bağlantıya tıklayın:
            {verification_url}

            Teşekkürler,
            Ekip
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
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cur.fetchone()

                if user:
                    if check_password_hash(user['password'], password):
                        if not user['is_active']:
                            flash("Hesabınız aktif değil. Lütfen e-posta adresinize gelen doğrulama bağlantısını tıklayın.", "danger")
                            return redirect(url_for('index'))

                        session['user_id'] = email
                        flash("Giriş başarılı!", "success")
                        return redirect(url_for('hello'))
                    else:
                        flash("Şifre hatalı. Lütfen tekrar deneyin.", "danger")
                else:
                    flash("E-posta adresi bulunamadı. Lütfen kayıt olun.", "danger")
        except Exception as e:
            print(f"Giriş hatası: {e}")
            flash("Bir hata oluştu. Lütfen tekrar deneyin.", "danger")
    return render_template('login.html')

@app.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute('SELECT * FROM users WHERE email = %s', (email,))
                user = cur.fetchone()
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
                    flash(f"Şifre sıfırlama bağlantısı '{email}' adresine gönderildi.", "success")
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
        confirm_password = request.form.get('confirm_password')

        if new_password != confirm_password:
            flash("Şifreler uyuşmuyor. Lütfen tekrar deneyin.", "danger")
            return render_template('reset_password.html', email=email)

        hashed_password = generate_password_hash(new_password, method='pbkdf2:sha256')
        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute('UPDATE users SET password = %s WHERE email = %s', (hashed_password, email))
                conn.commit()
                flash("Şifreniz başarıyla sıfırlandı. Lütfen giriş yapın.", "success")
                return redirect(url_for('login'))
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
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute('SELECT * FROM users WHERE email = %s', (email,))
            user = cur.fetchone()

        if request.method == 'POST':
            updated_data = {
                "first_name": request.form.get('first_name'),
                "last_name": request.form.get('last_name'),
                "profile_photo": request.form.get('profile_photo'),
            }
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute('''UPDATE users SET first_name = %s, last_name = %s, profile_photo = %s WHERE email = %s''',
                            (updated_data['first_name'], updated_data['last_name'], updated_data['profile_photo'], email))
                conn.commit()
            flash("Bilgileriniz başarıyla güncellendi.", "success")
    except Exception as e:
        print(f"Bilgi güncelleme hatası: {e}")
        flash("Bilgiler güncellenirken bir hata oluştu.", "danger")

    return render_template('hello.html', user=user)

@app.route('/verify', methods=['GET'])
def verify():
    email = request.args.get('email')

    try:
        with get_db_connection() as conn:
            cur = conn.cursor()
            cur.execute('UPDATE users SET is_active = TRUE WHERE email = %s', (email,))
            conn.commit()
            flash("E-posta doğrulama başarılı! Artık giriş yapabilirsiniz.", "success")
            return redirect(url_for('login'))
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

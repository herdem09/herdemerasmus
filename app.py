from flask import Flask, request, render_template, jsonify, redirect, url_for, session
import threading
import time
import hashlib
import secrets
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(16))

# Global değişkenler
veri = {
    "sicaklik": 25,
    "isik": 0,
    "vantilator": False,
    "pencere": False,
    "isitici": False,
    "kapi": False,
    "perde": True,
    "ampul": True,
    "sicaklik_oto": False,
    "isik_oto": False,
    "kapi_oto": False,
    "sicaklik1": 18,
    "sicaklik2": 22,
    "sicaklik3": 26
}

# API erişim anahtarı
API_KEY = os.environ.get('API_KEY', 'gizli_api_anahtari_degistirin')

# Kullanıcı bilgileri - gerçek uygulamada veritabanında saklanmalı
users = {
    "admin": {
        "password": hashlib.sha256("admin123".encode()).hexdigest(),
        "role": "admin"
    },
    "user": {
        "password": hashlib.sha256("user123".encode()).hexdigest(),
        "role": "user"
    }
}

# Oturum kontrolü decorator'ı
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# API anahtarı kontrolü
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        
        # API anahtarı kontrol et
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Yetkilendirme başarısız", "status": "error"}), 401
        
        token = auth_header.split(' ')[1]
        if token != API_KEY:
            return jsonify({"error": "Geçersiz API anahtarı", "status": "error"}), 401
            
        return f(*args, **kwargs)
    return decorated_function

# Kapı değişkeninin 5 saniye sonra False olarak değişmesi için
def kapi_reset():
    time.sleep(5)
    veri["kapi"] = False
    print("Kapı kapatıldı!")
    
    # Kapı oto aktifse ve kapı açıksa
    if veri["kapi_oto"] and not veri["kapi"]:
        # Zaman içinde kapıyı kontrol et
        time.sleep(10)  # 10 saniye bekleyerek simülasyon yapalım
        if not veri["kapi"]:  # Eğer kapı hala kapalıysa
            veri["kapi"] = True
            print("Otomatik kapı açıldı!")
            threading.Thread(target=kapi_reset).start()  # 5 saniye sonra tekrar kapat

# Otomatik kontrol fonksiyonları
def sicaklik_kontrol():
    sicaklik = veri["sicaklik"]
    if veri["sicaklik_oto"]:
        if sicaklik < veri["sicaklik1"]:
            veri["vantilator"] = False
            veri["pencere"] = False
            veri["isitici"] = True
        elif sicaklik < veri["sicaklik2"]:
            veri["vantilator"] = False
            veri["pencere"] = False
            veri["isitici"] = False
        elif sicaklik < veri["sicaklik3"]:
            veri["vantilator"] = False
            veri["pencere"] = True
            veri["isitici"] = False
        else:
            veri["vantilator"] = True
            veri["pencere"] = True
            veri["isitici"] = False

def isik_kontrol():
    if veri["isik_oto"]:
        if veri["isik"] == 0:
            veri["perde"] = True
            veri["ampul"] = True
        else:
            veri["perde"] = False
            veri["ampul"] = False

# Kapı otomatik açma-kapama simülasyonu - gerçek uygulamada sensörlerle entegre edilir
def kapi_oto_kontrol():
    print("Kapı otomatik kontrol başlatıldı")
    while True:
        if veri["kapi_oto"]:
            # Bu örnekte sadece zamana bağlı olarak kapıyı açıp kapatıyoruz
            # Gerçek uygulamada hareket sensörü, zaman programı, vb. kullanılabilir
            current_hour = time.localtime().tm_hour
            
            # Örnek: Belirli saatlerde kapıyı otomatik aç (burada 7-9 ve 17-19 arası)
            if (7 <= current_hour < 9 or 17 <= current_hour < 19) and not veri["kapi"]:
                veri["kapi"] = True
                print("Otomatik kapı programlı şekilde açıldı!")
                threading.Thread(target=kapi_reset).start()
                
        time.sleep(60)  # Her dakika kontrol et

# Kapı oto kontrol iş parçacığını başlat
kapi_thread = threading.Thread(target=kapi_oto_kontrol)
kapi_thread.daemon = True
kapi_thread.start()

@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        # Kullanıcı kontrolü
        if username in users and users[username]["password"] == hashlib.sha256(password.encode()).hexdigest():
            session['username'] = username
            session['role'] = users[username]["role"]
            
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('index'))
        else:
            error = 'Geçersiz kullanıcı adı veya şifre'
    
    return render_template('login.html', error=error)

@app.route('/logout')
def logout():
    session.pop('username', None)
    session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/')
@login_required
def index():
    return render_template('index.html', veri=veri, username=session.get('username'), role=session.get('role'))

# API endpoint - Tüm değerleri görüntüleme
@app.route('/api/veri', methods=['GET'])
@api_key_required
def get_veri():
    return jsonify(veri)

# API endpoint - Değerleri güncelleme
@app.route('/api/veri', methods=['POST'])
@api_key_required
def update_veri():
    data = request.get_json()
    
    # Güncelleme işlemleri
    for key, value in data.items():
        if key in veri:
            # Sıcaklık ve ışık için özel durumlar
            if key == "sicaklik":
                veri[key] = int(value)
                sicaklik_kontrol()
            elif key == "isik":
                veri[key] = int(value)
                isik_kontrol()
            # Kapı için özel durum
            elif key == "kapi" and value == True and veri[key] == False:
                veri[key] = True
                threading.Thread(target=kapi_reset).start()
            # Kapı oto kontrol için özel durum
            elif key == "kapi_oto":
                veri[key] = bool(value)
            # Sıcaklık oto kontrolü için özel durum
            elif key == "sicaklik_oto":
                veri[key] = bool(value)
                if veri[key]:
                    sicaklik_kontrol()
            # Işık oto kontrolü için özel durum
            elif key == "isik_oto":
                veri[key] = bool(value)
                if veri[key]:
                    isik_kontrol()
            # Vantilator, pencere, isitici kontrolleri
            elif key in ["vantilator", "pencere", "isitici"] and not veri["sicaklik_oto"]:
                veri[key] = bool(value)
            # Perde, ampul kontrolleri
            elif key in ["perde", "ampul"] and not veri["isik_oto"]:
                veri[key] = bool(value)
            # Sıcaklık eşik değerleri
            elif key in ["sicaklik1", "sicaklik2", "sicaklik3"]:
                veri[key] = int(value)
                if veri["sicaklik_oto"]:
                    sicaklik_kontrol()
    
    return jsonify({"status": "success", "veri": veri})

# ESP için özel endpoint
@app.route('/api/esp', methods=['GET'])
@api_key_required
def get_esp_veri():
    # ESP'nin görebileceği değişkenleri içeren sözlük
    esp_veri = {
        "vantilator": veri["vantilator"],
        "pencere": veri["pencere"],
        "isitici": veri["isitici"],
        "kapi": veri["kapi"],
        "perde": veri["perde"],
        "ampul": veri["ampul"]
    }
    return jsonify(esp_veri)

# ESP için güncelleme endpoint'i
@app.route('/api/esp', methods=['POST'])
@api_key_required
def update_esp_veri():
    data = request.get_json()
    
    for key, value in data.items():
        if key in ["vantilator", "pencere", "isitici", "kapi", "perde", "ampul"]:
            # Kapı için özel durum
            if key == "kapi" and value == True and veri[key] == False:
                veri[key] = True
                threading.Thread(target=kapi_reset).start()
            # Sıcaklık oto kontrolü açıkken vantilator, pencere, isitici değiştirilemez
            elif key in ["vantilator", "pencere", "isitici"] and not veri["sicaklik_oto"]:
                veri[key] = bool(value)
            # Işık oto kontrolü açıkken perde, ampul değiştirilemez
            elif key in ["perde", "ampul"] and not veri["isik_oto"]:
                veri[key] = bool(value)
    
    esp_veri = {
        "vantilator": veri["vantilator"],
        "pencere": veri["pencere"],
        "isitici": veri["isitici"],
        "kapi": veri["kapi"],
        "perde": veri["perde"],
        "ampul": veri["ampul"]
    }
    
    return jsonify({"status": "success", "veri": esp_veri})

# API anahtarı generator - sadece admin kullanabilir
@app.route('/generate-api-key', methods=['GET'])
@login_required
def generate_api_key():
    if session.get('role') != 'admin':
        return jsonify({"error": "Bu işlem için yetkiniz yok", "status": "error"}), 403
        
    # Yeni API anahtarı oluştur - gerçek uygulamada daha güvenli bir yöntem kullanılmalı
    global API_KEY
    API_KEY = secrets.token_hex(16)
    
    return jsonify({"api_key": API_KEY, "status": "success"})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

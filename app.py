from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import os
import time
import threading
import json
from functools import wraps
import hashlib

app = Flask(__name__)
app.secret_key = os.urandom(24)

# Başlangıç değerleri
data = {
    "sicaklik": 25,
    "isik": 0,
    "vantilator": False,
    "pencere": False,
    "isitici": False,
    "kapi": False,
    "perde": True,
    "ampul": True,
    "sicaklik_oto": False,
    "isik_oto": True,
    "sicaklik1": 18,
    "sicaklik2": 23,
    "sicaklik3": 27,
    "kapi_oto": True
}

# API anahtarı oluşturma ve doğrulama
API_KEY = "gizli_anahtar_123"

def verify_api_key(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if request.method == 'GET':
            api_key = request.args.get('api_key')
        else:
            api_key = request.json.get('api_key')
        
        if api_key != API_KEY:
            return jsonify({"error": "Geçersiz API anahtarı"}), 401
        return func(*args, **kwargs)
    return wrapper

# Oturum kontrolü
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Kapı otomatik kapatma fonksiyonu
def close_door():
    time.sleep(5)
    data["kapi"] = False

# Otomatik kontroller
def check_auto_controls():
    if data["sicaklik_oto"]:
        sicaklik = data["sicaklik"]
        if sicaklik < data["sicaklik1"]:
            data["vantilator"] = False
            data["pencere"] = False
            data["isitici"] = True
        elif sicaklik < data["sicaklik2"]:
            data["vantilator"] = False
            data["pencere"] = False
            data["isitici"] = False
        elif sicaklik < data["sicaklik3"]:
            data["vantilator"] = False
            data["pencere"] = True
            data["isitici"] = False
        else:
            data["vantilator"] = True
            data["pencere"] = True
            data["isitici"] = False
    
    if data["isik_oto"]:
        if data["isik"] == 0:  # Karanlık
            data["perde"] = True
            data["ampul"] = True
        else:  # Aydınlık
            data["perde"] = False
            data["ampul"] = False

# Ana sayfa
@app.route('/')
@login_required
def index():
    check_auto_controls()
    return render_template('index.html', data=data)

# Giriş sayfası
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'herdem' and password == '1940':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Geçersiz kullanıcı adı veya şifre')
    
    return render_template('login.html')

# Çıkış
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Web sitesinden değer güncelleme
@app.route('/update', methods=['POST'])
@login_required
def update():
    field = request.form.get('field')
    value = request.form.get('value')
    
    if field in ['sicaklik', 'isik']:
        return jsonify({"error": "Bu değerler web arayüzünden değiştirilemez"}), 400
    
    if field == 'kapi' and data['kapi_oto']:
        return jsonify({"error": "Kapı otomatik modda iken değiştirilemez"}), 400
    
    if (field in ['vantilator', 'pencere', 'isitici']) and data['sicaklik_oto']:
        return jsonify({"error": "Sıcaklık otomatik modda iken bu değer değiştirilemez"}), 400
    
    if (field in ['perde', 'ampul']) and data['isik_oto']:
        return jsonify({"error": "Işık otomatik modda iken bu değer değiştirilemez"}), 400
    
    # Değer dönüşümleri
    if field in ['sicaklik', 'sicaklik1', 'sicaklik2', 'sicaklik3']:
        data[field] = int(value)
    elif field in ['vantilator', 'pencere', 'isitici', 'kapi', 'perde', 'ampul', 'sicaklik_oto', 'isik_oto', 'kapi_oto']:
        data[field] = value.lower() == 'true'
        
        # Kapı için otomatik kapatma
        if field == 'kapi' and data['kapi']:
            thread = threading.Thread(target=close_door)
            thread.daemon = True
            thread.start()
    
    check_auto_controls()
    return jsonify({"success": True})

# API'den tüm değişkenleri alma
@app.route('/api/get', methods=['GET'])
@verify_api_key
def api_get():
    check_auto_controls()
    return jsonify(data)

# API'den belirli değişkenleri alma (ESP için)
@app.route('/api/get_esp', methods=['GET'])
def api_get_esp():
    esp_data = {
        "vantilator": data["vantilator"],
        "pencere": data["pencere"],
        "isitici": data["isitici"],
        "kapi": data["kapi"],
        "perde": data["perde"],
        "ampul": data["ampul"]
    }
    return jsonify(esp_data)

# API'den değer güncelleme
@app.route('/api/update', methods=['POST'])
@verify_api_key
def api_update():
    updates = request.json
    
    for field, value in updates.items():
        if field != 'api_key':
            if field == 'kapi' and data['kapi_oto']:
                continue
            
            if (field in ['vantilator', 'pencere', 'isitici']) and data['sicaklik_oto']:
                continue
            
            if (field in ['perde', 'ampul']) and data['isik_oto']:
                continue
            
            # Değişkeni güncelle
            data[field] = value
            
            # Kapı için otomatik kapatma
            if field == 'kapi' and data['kapi']:
                thread = threading.Thread(target=close_door)
                thread.daemon = True
                thread.start()
    
    check_auto_controls()
    return jsonify({"success": True})

# HTML şablonları
@app.route('/templates')
def serve_templates():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Ev Otomasyon Sistemi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; max-width: 800px; margin: 0 auto; padding: 20px; }
        .container { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; }
        .card { border: 1px solid #ddd; padding: 15px; border-radius: 8px; margin-bottom: 15px; }
        .status { font-weight: bold; }
        .controls { margin-top: 20px; }
        button { padding: 8px 12px; cursor: pointer; }
        .true { color: green; }
        .false { color: red; }
        input[type="number"] { width: 60px; }
    </style>
</head>
<body>
    <h1>Ev Otomasyon Kontrol Paneli</h1>
    <div class="card">
        <h2>Sistem Durumu</h2>
        <div class="container">
            <div>Sıcaklık: <span class="status">{{ data.sicaklik }}°C</span></div>
            <div>Işık: <span class="status {{ 'true' if data.isik else 'false' }}">{{ 'Açık' if data.isik else 'Kapalı' }}</span></div>
            <div>Vantilatör: <span class="status {{ 'true' if data.vantilator else 'false' }}">{{ 'Açık' if data.vantilator else 'Kapalı' }}</span></div>
            <div>Pencere: <span class="status {{ 'true' if data.pencere else 'false' }}">{{ 'Açık' if data.pencere else 'Kapalı' }}</span></div>
            <div>Isıtıcı: <span class="status {{ 'true' if data.isitici else 'false' }}">{{ 'Açık' if data.isitici else 'Kapalı' }}</span></div>
            <div>Kapı: <span class="status {{ 'true' if data.kapi else 'false' }}">{{ 'Açık' if data.kapi else 'Kapalı' }}</span></div>
            <div>Perde: <span class="status {{ 'true' if data.perde else 'false' }}">{{ 'Açık' if data.perde else 'Kapalı' }}</span></div>
            <div>Ampul: <span class="status {{ 'true' if data.ampul else 'false' }}">{{ 'Açık' if data.ampul else 'Kapalı' }}</span></div>
            <div>Sıcaklık Oto: <span class="status {{ 'true' if data.sicaklik_oto else 'false' }}">{{ 'Açık' if data.sicaklik_oto else 'Kapalı' }}</span></div>
            <div>Işık Oto: <span class="status {{ 'true' if data.isik_oto else 'false' }}">{{ 'Açık' if data.isik_oto else 'Kapalı' }}</span></div>
            <div>Kapı Oto: <span class="status {{ 'true' if data.kapi_oto else 'false' }}">{{ 'Açık' if data.kapi_oto else 'Kapalı' }}</span></div>
            <div>Sıcaklık 1: <span class="status">{{ data.sicaklik1 }}°C</span></div>
            <div>Sıcaklık 2: <span class="status">{{ data.sicaklik2 }}°C</span></div>
            <div>Sıcaklık 3: <span class="status">{{ data.sicaklik3 }}°C</span></div>
        </div>
    </div>
    
    <div class="card">
        <h2>Kontroller</h2>
        <div class="controls">
            <h3>Cihaz Kontrolleri</h3>
            <div>
                <button onclick="updateValue('vantilator', !{{ 'true' if data.vantilator else 'false' }})" {{ 'disabled' if data.sicaklik_oto else '' }}>
                    Vantilatör {{ 'Kapat' if data.vantilator else 'Aç' }}
                </button>
            </div>
            <div>
                <button onclick="updateValue('pencere', !{{ 'true' if data.pencere else 'false' }})" {{ 'disabled' if data.sicaklik_oto else '' }}>
                    Pencere {{ 'Kapat' if data.pencere else 'Aç' }}
                </button>
            </div>
            <div>
                <button onclick="updateValue('isitici', !{{ 'true' if data.isitici else 'false' }})" {{ 'disabled' if data.sicaklik_oto else '' }}>
                    Isıtıcı {{ 'Kapat' if data.isitici else 'Aç' }}
                </button>
            </div>
            <div>
                <button onclick="updateValue('kapi', true)" {{ 'disabled' if data.kapi_oto else '' }}>
                    Kapıyı Aç
                </button>
            </div>
            <div>
                <button onclick="updateValue('perde', !{{ 'true' if data.perde else 'false' }})" {{ 'disabled' if data.isik_oto else '' }}>
                    Perde {{ 'Kapat' if data.perde else 'Aç' }}
                </button>
            </div>
            <div>
                <button onclick="updateValue('ampul', !{{ 'true' if data.ampul else 'false' }})" {{ 'disabled' if data.isik_oto else '' }}>
                    Ampul {{ 'Kapat' if data.ampul else 'Aç' }}
                </button>
            </div>
            
            <h3>Otomatik Mod Kontrolleri</h3>
            <div>
                <button onclick="updateValue('sicaklik_oto', !{{ 'true' if data.sicaklik_oto else 'false' }})">
                    Sıcaklık Oto {{ 'Kapat' if data.sicaklik_oto else 'Aç' }}
                </button>
            </div>
            <div>
                <button onclick="updateValue('isik_oto', !{{ 'true' if data.isik_oto else 'false' }})">
                    Işık Oto {{ 'Kapat' if data.isik_oto else 'Aç' }}
                </button>
            </div>
            <div>
                <button onclick="updateValue('kapi_oto', !{{ 'true' if data.kapi_oto else 'false' }})">
                    Kapı Oto {{ 'Kapat' if data.kapi_oto else 'Aç' }}
                </button>
            </div>
            
            <h3>Sıcaklık Ayarları</h3>
            <div>
                <label>Sıcaklık 1: </label>
                <input type="number" id="sicaklik1" value="{{ data.sicaklik1 }}">
                <button onclick="updateValue('sicaklik1', document.getElementById('sicaklik1').value)">Güncelle</button>
            </div>
            <div>
                <label>Sıcaklık 2: </label>
                <input type="number" id="sicaklik2" value="{{ data.sicaklik2 }}">
                <button onclick="updateValue('sicaklik2', document.getElementById('sicaklik2').value)">Güncelle</button>
            </div>
            <div>
                <label>Sıcaklık 3: </label>
                <input type="number" id="sicaklik3" value="{{ data.sicaklik3 }}">
                <button onclick="updateValue('sicaklik3', document.getElementById('sicaklik3').value)">Güncelle</button>
            </div>
        </div>
    </div>
    <div>
        <a href="/logout">Çıkış Yap</a>
    </div>
    
    <script>
        function updateValue(field, value) {
            const formData = new FormData();
            formData.append('field', field);
            formData.append('value', value);
            
            fetch('/update', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    alert(data.error);
                } else {
                    window.location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Bir hata oluştu.');
            });
        }
    </script>
</body>
</html>
"""

@app.route('/templates/login')
def serve_login_template():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Giriş - Ev Otomasyon Sistemi</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; max-width: 500px; margin: 0 auto; padding: 20px; }
        .login-container { border: 1px solid #ddd; padding: 20px; border-radius: 8px; }
        .form-group { margin-bottom: 15px; }
        input { width: 100%; padding: 8px; box-sizing: border-box; }
        button { padding: 10px 15px; background-color: #4CAF50; color: white; border: none; cursor: pointer; }
        .error { color: red; margin-bottom: 15px; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2>Ev Otomasyon Sistemi</h2>
        <form method="post" action="/login">
            {% if error %}
            <div class="error">{{ error }}</div>
            {% endif %}
            <div class="form-group">
                <label for="username">Kullanıcı Adı:</label>
                <input type="text" id="username" name="username" required>
            </div>
            <div class="form-group">
                <label for="password">Şifre:</label>
                <input type="password" id="password" name="password" required>
            </div>
            <button type="submit">Giriş</button>
        </form>
    </div>
</body>
</html>
"""

@app.route('/templates/index')
def serve_index_template():
    return render_template('index.html', data=data)

# HTML şablonları render_template için override
def render_template(template_name, **context):
    if template_name == 'index.html':
        return app.route('/templates')()
    elif template_name == 'login.html':
        error_message = context.get('error', '')
        template = app.route('/templates/login')()
        return template.replace('{% if error %}\n            <div class="error">{{ error }}</div>\n            {% endif %}', 
                              f'<div class="error">{error_message}</div>' if error_message else '')
    return f"Template not found: {template_name}"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

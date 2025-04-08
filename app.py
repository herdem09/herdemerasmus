from flask import Flask, request, render_template, redirect, session, jsonify, url_for
import time
import threading
import os
from functools import wraps
import json

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', os.urandom(24))

# Global variables
data = {
    "sicaklik": 25,
    "isik": 0,
    "vantilator": False,
    "pencere": False,
    "isitici": False,
    "kapi": False,
    "perde": True,  # isik 0 olduğunda True
    "ampul": True,  # isik 0 olduğunda True
    "sicaklik_oto": False,
    "isik_oto": False,
    "kapioto": False,
    "sicaklik1": 18,
    "sicaklik2": 22,
    "sicaklik3": 26
}

api_key = os.environ.get('API_KEY', "gizli_anahtar123")  # API anahtarı

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# API key required decorator
def api_key_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get('API-Key') != api_key:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Auto door close function
def auto_close_door():
    time.sleep(5)
    data["kapi"] = False

# Auto climate control function
def update_climate_control():
    if data["sicaklik_oto"]:
        if data["sicaklik"] < data["sicaklik1"]:
            data["vantilator"] = False
            data["pencere"] = False
            data["isitici"] = True
        elif data["sicaklik"] < data["sicaklik2"]:
            data["vantilator"] = False
            data["pencere"] = False
            data["isitici"] = False
        elif data["sicaklik"] < data["sicaklik3"]:
            data["vantilator"] = False
            data["pencere"] = True
            data["isitici"] = False
        else:
            data["vantilator"] = True
            data["pencere"] = True
            data["isitici"] = False

# Auto light control function
def update_light_control():
    if data["isik_oto"]:
        if data["isik"] == 0:
            data["perde"] = True
            data["ampul"] = True
        else:
            data["perde"] = False
            data["ampul"] = False

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if username == 'herdem' and password == '1940':
            session['logged_in'] = True
            return redirect(url_for('index'))
        else:
            return render_template('login.html', error='Geçersiz kullanıcı adı veya şifre')
    
    return render_template('login.html')

# Logout
@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

# Main page
@app.route('/')
@login_required
def index():
    update_climate_control()
    update_light_control()
    return render_template('index.html', data=data)

# Web update endpoint
@app.route('/update', methods=['POST'])
@login_required
def update():
    for key in request.form:
        if key in data:
            value = request.form[key]
            
            # Type conversion
            if key in ["sicaklik", "isik", "sicaklik1", "sicaklik2", "sicaklik3"]:
                value = int(value)
            elif key in ["vantilator", "pencere", "isitici", "kapi", "perde", "ampul", "sicaklik_oto", "isik_oto", "kapioto"]:
                value = (value.lower() == 'true')
            
            # Rule checks
            if key in ["vantilator", "pencere", "isitici"] and data["sicaklik_oto"]:
                continue
            if key in ["perde", "ampul"] and data["isik_oto"]:
                continue
            if key == "kapi" and data["kapioto"]:
                continue
            
            # Update value
            data[key] = value
            
            # Special case for door
            if key == "kapi" and value == True:
                threading.Thread(target=auto_close_door, daemon=True).start()
    
    update_climate_control()
    update_light_control()
    return redirect(url_for('index'))

# API Endpoints for Python and ESP clients
@app.route('/api/data', methods=['GET'])
@api_key_required
def get_data():
    response = data.copy()
    
    # Add client type parameter
    client_type = request.args.get('client', 'python')
    
    # For ESP clients, filter out sicaklik and isik
    if client_type == 'esp':
        filtered_data = {k: v for k, v in response.items() if k not in ["sicaklik", "isik"]}
        return jsonify(filtered_data)
    
    return jsonify(response)

@app.route('/api/update', methods=['POST'])
@api_key_required
def api_update():
    update_data = request.json
    
    for key, value in update_data.items():
        if key in data:
            # Rule checks
            if key in ["vantilator", "pencere", "isitici"] and data["sicaklik_oto"]:
                continue
            if key in ["perde", "ampul"] and data["isik_oto"]:
                continue
            if key == "kapi" and data["kapioto"]:
                continue
            
            # Update value
            data[key] = value
            
            # Special case for door
            if key == "kapi" and value == True:
                threading.Thread(target=auto_close_door, daemon=True).start()
    
    update_climate_control()
    update_light_control()
    return jsonify({"status": "success"})

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

from flask import Flask, request, jsonify, render_template, redirect, url_for, session
from functools import wraps
import time
import threading

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Kullanıcı girişi ve API şifreleme
USERNAME = 'herdem'
PASSWORD = '1940'
API_KEY = 'api_secret_key'

# Global değişkenler
state = {
    'sicaklik': 20,
    'isik': 0,
    'vantilator': False,
    'pencere': False,
    'isitici': False,
    'kapi': False,
    'perde': False,
    'ampul': False,
    'sicaklik_oto': False,
    'isik_oto': False,
    'sicaklik1': 18,
    'sicaklik2': 21,
    'sicaklik3': 24,
    'kapioto': False
}

# Kapi otomatik kapanma
kapi_lock = threading.Lock()
def auto_reset_kapi():
    time.sleep(5)
    with kapi_lock:
        state['kapi'] = False

# Giriş kontrolü

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    return render_template('index.html', state=state)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        if request.form['username'] == USERNAME and request.form['password'] == PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('index'))
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/update', methods=['POST'])
@login_required
def update():
    for key in request.form:
        value = request.form[key]
        if key in state:
            if key in ['sicaklik', 'isik', 'sicaklik1', 'sicaklik2', 'sicaklik3']:
                state[key] = int(value)
            else:
                value = value == 'true'
                if key == 'kapi' and state['kapioto']:
                    continue
                if key in ['vantilator', 'pencere', 'isitici'] and state['sicaklik_oto']:
                    continue
                if key in ['perde', 'ampul'] and state['isik_oto']:
                    continue
                state[key] = value
                if key == 'kapi' and value:
                    threading.Thread(target=auto_reset_kapi).start()
    apply_auto_logic()
    return redirect(url_for('index'))

@app.route('/api', methods=['POST'])
def api():
    data = request.json
    if not data or data.get('key') != API_KEY:
        return jsonify({'error': 'Unauthorized'}), 401

    if 'get' in data:
        result = {k: state[k] for k in data['get'] if k in state}
        return jsonify(result)
    if 'set' in data:
        for key, value in data['set'].items():
            if key not in state:
                continue
            if key == 'kapi' and state['kapioto']:
                continue
            if isinstance(state[key], bool):
                value = bool(value)
            elif isinstance(state[key], int):
                value = int(value)
            state[key] = value
            if key == 'kapi' and value:
                threading.Thread(target=auto_reset_kapi).start()
        apply_auto_logic()
        return jsonify({'status': 'updated'})
    return jsonify({'error': 'Invalid request'})

def apply_auto_logic():
    if state['isik'] == 0:
        state['perde'] = True
        state['ampul'] = True
    else:
        state['perde'] = False
        state['ampul'] = False

    if state['sicaklik_oto']:
        if state['sicaklik'] < state['sicaklik1']:
            state['vantilator'] = False
            state['pencere'] = False
            state['isitici'] = True
        elif state['sicaklik'] < state['sicaklik2']:
            state['vantilator'] = False
            state['pencere'] = False
            state['isitici'] = False
        elif state['sicaklik'] < state['sicaklik3']:
            state['vantilator'] = False
            state['pencere'] = True
            state['isitici'] = False
        else:
            state['vantilator'] = True
            state['pencere'] = True
            state['isitici'] = False

if __name__ == '__main__':
    app.run(debug=True)

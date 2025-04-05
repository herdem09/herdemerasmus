from flask import Flask, request, render_template, jsonify
import threading
import time

app = Flask(__name__)

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
    "sicaklik1": 18,
    "sicaklik2": 22,
    "sicaklik3": 26
}

# Kapı değişkeninin 5 saniye sonra False olarak değişmesi için
def kapi_reset():
    time.sleep(5)
    veri["kapi"] = False
    print("Kapı kapatıldı!")

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

@app.route('/')
def index():
    return render_template('index.html', veri=veri)

# API endpoint - Tüm değerleri görüntüleme
@app.route('/api/veri', methods=['GET'])
def get_veri():
    return jsonify(veri)

# API endpoint - Değerleri güncelleme
@app.route('/api/veri', methods=['POST'])
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
    
    return jsonify({"status": "success", "veri": esp_veri()})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import re
import os
import serial
import serial.tools.list_ports
import threading

app = Flask(__name__)
# On autorise les connexions cross-origin pour éviter les blocages du navigateur
socketio = SocketIO(app, cors_allowed_origins="*")

CPP_FILE = "Arduino/Librairie_CAPTEUR_LED/config.cpp"

# Variables globales pour la gestion série
ser_instance = None
serial_thread = None
stop_event = threading.Event()

# =========================================================
# LOGIQUE D'EXTRACTION & SAUVEGARDE
# =========================================================
def extract_array(content, name):
    pattern = rf'(uint8_t|int16_t|int)\s+{name}\s*\[\s*64\s*\]\s*=\s*\{{(.*?)\}};'
    match = re.search(pattern, content, re.S)
    if not match:
        return [], None
    type_name = match.group(1)
    raw_values = match.group(2)
    numbers = re.findall(r'0x[0-9A-Fa-f]+|-?\d+', raw_values)
    values = [int(num, 16) if num.startswith("0x") else int(num) for num in numbers]
    return values, type_name

def replace_array(content, name, values, type_name):
    new_array = f"{type_name} {name}[64] = {{\n"
    for i in range(0, 64, 8):
        line = [f"0x{v:02X}" if type_name == "uint8_t" else str(v) for v in values[i:i+8]]
        new_array += "    " + ",".join(line) + ",\n"
    new_array = new_array.rstrip(",\n") + "\n};"
    pattern = rf'(uint8_t|int16_t|int)\s+{name}\s*\[\s*64\s*\]\s*=\s*\{{.*?\}};'
    return re.sub(pattern, new_array, content, flags=re.S)

# =========================================================
# GESTION DYNAMIQUE DU PORT SERIE
# =========================================================
def serial_reader(port):
    global ser_instance
    try:
        # Configuration de la vitesse à 115200 comme dans l'Arduino [cite: 1]
        ser_instance = serial.Serial(port, 115200, timeout=1)
        print(f"Port série ouvert : {port}")
        
        # On informe le front-end que la connexion est réussie
        socketio.emit('connection_status', {'status': 'connecté'})

        while not stop_event.is_set():
            # On attend le header 0xAA 0xBB envoyé par l'Arduino [cite: 2]
            if ser_instance.in_waiting >= 2:
                header = ser_instance.read(2)
                if header == b'\xaa\xbb':
                    # On lit les 256 octets de données (64 cases * 4 octets) [cite: 6, 8]
                    payload = ser_instance.read(64 * 4)
                    data_board = []
                    
                    for i in range(0, len(payload), 4):
                        case_id = payload[i] # Index (0-63) [cite: 7]
                        # Reconstruction du int16 (Z) à partir du High et Low byte [cite: 5, 6]
                        z_val = int.from_bytes(payload[i+1:i+3], byteorder='big', signed=True)
                        etat = payload[i+3] # État du pion (0, 1, 2) [cite: 4]
                        
                        data_board.append({"id": case_id, "z": z_val, "etat": etat})
                    
                    # On lit l'octet de checksum final pour vider le buffer 
                    if ser_instance.in_waiting > 0:
                        ser_instance.read(1)
                        
                    # Envoi en temps réel via SocketIO
                    socketio.emit('update_board', data_board)
                elif header == b'\xcc\xdd':
                        print("🔍 Scan I2C détecté !")
                        found_addresses = []
                        # On lit jusqu'à trouver 0xFF (fin du scan)
                        while True:
                            addr_byte = ser_instance.read(1)
                            if not addr_byte or addr_byte == b'\xff':
                                break
                            found_addresses.append(hex(ord(addr_byte)))
                        
                        print(f" Adresses trouvées : {found_addresses}")
                        socketio.emit('i2c_results', found_addresses)
                elif header == b'\xee\xee':
                        print("retour Offset")
                        found_addresses = []
                        # On lit jusqu'à trouver 0xFF (fin du scan)
                        while True:
                            addr_byte = ser_instance.read(1)
                            if not addr_byte or addr_byte == b'\xff':
                                break
                            found_addresses.append(hex(ord(addr_byte)))
                        
                        print(f" retour offset {found_addresses}")
                        socketio.emit('return_offset', found_addresses)
    except Exception as e:
        print(f"Erreur série : {e}")
        socketio.emit('connection_status', {'status': 'déconnecté'})
    finally:
        if ser_instance and ser_instance.is_open:
            ser_instance.close()
        ser_instance = None
        socketio.emit('connection_status', {'status': 'déconnecté'})
        print("Port série fermé")

# =========================================================
# ROUTES FLASK (CORRIGÉES POUR CORRESPONDRE AU HTML)
# =========================================================
@app.route("/")
def home():
    return render_template("home.html")

@app.route("/config")
def config():
    if not os.path.exists(CPP_FILE):
        return "Fichier config.cpp introuvable"
    with open(CPP_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    addr, _ = extract_array(content, "A31301_ADDR")
    led, _ = extract_array(content, "tab_LED")
    seuil, _ = extract_array(content, "SEUIL_CAPT")

    data = {
        "addrI2C": addr or [0]*64,
        "seuil1": led or [0]*64,
        "seuil2": seuil or [0]*64
    }
    return render_template("index.html", data=data)

@app.route("/save", methods=["POST"])
def save():
    new_data = request.json
    with open(CPP_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    for name, key in zip(["A31301_ADDR", "tab_LED", "SEUIL_CAPT"], ["addrI2C", "seuil1", "seuil2"]):
        values, type_name = extract_array(content, name)
        content = replace_array(content, name, new_data[key], type_name)

    with open(CPP_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    return jsonify({"status": "ok"})

@app.route("/live")
def live():
    # Liste les ports COM disponibles pour le menu déroulant
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return render_template("live.html", ports=ports)

# =========================================================
# ENDPOINTS DE CONTRÔLE SÉRIE
# =========================================================
@app.route("/connect", methods=["POST"])
def api_connect():
    global serial_thread, stop_event, ser_instance
    
    # Récupération du port envoyé en JSON par le bouton "Se connecter"
    data = request.get_json()
    port = data.get('port')
    
    if not port:
        return jsonify({"status": "error", "message": "Aucun port spécifié"}), 400

    # Arrêter proprement une ancienne connexion si elle existe
    if ser_instance and ser_instance.is_open:
        stop_event.set()
        ser_instance.close()
    
    stop_event.clear()
    serial_thread = threading.Thread(target=serial_reader, args=(port,), daemon=True)
    serial_thread.start()
    
    return jsonify({"status": "connecting", "port": port})

@app.route("/disconnect", methods=["POST"])
def api_disconnect():
    global ser_instance
    stop_event.set()
    if ser_instance and ser_instance.is_open:
        ser_instance.close()
    return jsonify({"status": "disconnected"})

@app.route("/I2C")
def i2c_page():
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return render_template("i2c.html", ports=ports)

@app.route("/OFFSET")
def offset_page():
    ports = [port.device for port in serial.tools.list_ports.comports()]
    return render_template("offset.html", ports=ports)

# Endpoint pour lancer le test
@app.route("/run_i2c_test", methods=["POST"])
def run_i2c_test():
    if ser_instance and ser_instance.is_open:
        ser_instance.write(b"test_I2C\n")
        return jsonify({"status": "sent"})
    return jsonify({"status": "error"}), 400

@app.route("/run_offset", methods=["POST"])
def run_offset():
    if ser_instance and ser_instance.is_open:
        ser_instance.write(b"offset\n")
        return jsonify({"status": "sent"})
    return jsonify({"status": "error"}), 400
# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    # Lancement du serveur (port 5000 par défaut)
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
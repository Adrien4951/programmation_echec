from flask import Flask, render_template, request, jsonify
import re
import os

app = Flask(__name__)

# Chemin relatif vers ton fichier config.cpp
CPP_FILE = "Arduino/Librairie_CAPTEUR_LED/config.cpp"


# =========================================================
# Extraction des tableaux (support uint8_t et int16_t)
# =========================================================
def extract_array(content, name):
    # Match uint8_t / int16_t / int avec [64]
    pattern = rf'(uint8_t|int16_t|int)\s+{name}\s*\[\s*64\s*\]\s*=\s*\{{(.*?)\}};'
    match = re.search(pattern, content, re.S)

    if not match:
        print(f"❌ Tableau {name} non trouvé")
        return [], None

    type_name = match.group(1)
    raw_values = match.group(2)

    # Capture nombres décimaux et hexadécimaux
    numbers = re.findall(r'0x[0-9A-Fa-f]+|-?\d+', raw_values)

    values = []
    for num in numbers:
        if num.startswith("0x"):
            values.append(int(num, 16))
        else:
            values.append(int(num))

    return values, type_name


# =========================================================
# Remplacement tableau dans le fichier
# =========================================================
def replace_array(content, name, values, type_name):
    new_array = f"{type_name} {name}[64] = {{\n"
    for i in range(0, 64, 8):
        line = []
        for v in values[i:i+8]:
            if type_name == "uint8_t":
                line.append(f"0x{v:02X}")
            else:
                line.append(str(v))
        new_array += "    " + ",".join(line) + ",\n"
    new_array = new_array.rstrip(",\n") + "\n};"

    pattern = rf'(uint8_t|int16_t|int)\s+{name}\s*\[\s*64\s*\]\s*=\s*\{{.*?\}};'
    return re.sub(pattern, new_array, content, flags=re.S)


# =========================================================
# Page principale
# =========================================================
@app.route("/")
def index():

    if not os.path.exists(CPP_FILE):
        return f"❌ Fichier introuvable : {CPP_FILE}"

    with open(CPP_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    addr, type1 = extract_array(content, "A31301_ADDR")
    led, type2 = extract_array(content, "tab_LED")
    seuil, type3 = extract_array(content, "SEUIL_CAPT")

    # Sécurité
    if len(addr) != 64: addr = [0]*64
    if len(led) != 64: led = [0]*64
    if len(seuil) != 64: seuil = [0]*64

    data = {
        "addrI2C": addr,
        "seuil1": led,
        "seuil2": seuil
    }

    return render_template("index.html", data=data)


# =========================================================
# Sauvegarde depuis le navigateur
# =========================================================
@app.route("/save", methods=["POST"])
def save():
    new_data = request.json

    with open(CPP_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    for name, key, type_name_key in zip(
        ["A31301_ADDR", "tab_LED", "SEUIL_CAPT"],
        ["addrI2C", "seuil1", "seuil2"],
        [None, None, None]  # type_name sera récupéré dynamiquement
    ):
        values, type_name = extract_array(content, name)
        content = replace_array(content, name, new_data[key], type_name)

    with open(CPP_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    return jsonify({"status": "ok"})


# =========================================================
if __name__ == "__main__":
    app.run(debug=True)
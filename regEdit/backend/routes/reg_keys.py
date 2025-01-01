from flask import Blueprint, jsonify, request
import winreg

register_key_bp = Blueprint("register_key", __name__)

def get_subkeys(path):
    subkeys = []

    try:
        top_level_keys = {"HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
            "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
            "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
            "HKEY_USERS": winreg.HKEY_USERS,
            "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG}

        if path in top_level_keys:
            key = top_level_keys[path]
            with winreg.OpenKey(key, "") as reg_key:
                index = 0
                while True:
                    try:
                        subkey = winreg.EnumKey(reg_key, index)
                        subkeys.append(subkey)
                        index += 1
                    except OSError:
                        break
        else:
            if "\\" not in path:
                return {"error": "True", "message": "expected '\\' in path"}

            key_name, new_path = path.split("\\", 1)
            key = getattr(winreg, key_name, None)
            if not key:
                return {"error": "True", "message": f"invalid key: {key_name}"}

            with winreg.OpenKey(key, new_path) as reg_key:
                index = 0
                while True:
                    try:
                        subkey = winreg.EnumKey(reg_key, index)
                        subkeys.append(subkey)
                        index += 1
                    except OSError:
                        break
    except Exception as e:
        return {"error" : "True", "message" : str(e)}
    return {"error": "False", "subkeys": {key: key for key in subkeys}}



@register_key_bp.route("/api/keys", methods=["GET"])
def get_registry_subkeys():
    path = request.args.get("path")
    if not path:
        return jsonify({"HKEY_CLASSES_ROOT": [],
            "HKEY_CURRENT_USER": [],
            "HKEY_LOCAL_MACHINE": [],
            "HKEY_USERS": [],
            "HKEY_CURRENT_CONFIG": []})

    rez = get_subkeys(path)
    if rez["error"] == "True":
        return jsonify({"error" : rez["message"]}), 400
    return jsonify({path: rez["subkeys"]})

@register_key_bp.route("/api/keys", methods=["POST"])
def create_key():
    data = request.json
    path = data.get("path")
    name = data.get("name")

    try:
        if "\\" not in path:
            key_name = path
            subpath = ""
        else:
            key_name, subpath = path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        with winreg.CreateKey(main_key, subpath + "\\" + name) as new_key:
            return jsonify({"message": f"Key '{key_name}' created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

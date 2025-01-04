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


@register_key_bp.route("/api/keys", methods=["DELETE"])
def delete_key():
    data = request.json
    path = data.get("key")

    try:
        if "\\" not in path:
            key_name = path
            subpath = ""
        else:
            key_name, subpath = path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        delete_key_rec(main_key, subpath)
        return jsonify({"message": f"Key '{path}' deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@register_key_bp.route("/api/keys", methods=["PUT"])
def rename_key():
    data = request.json
    path = data.get("path")
    new_name = data.get("new_name")

    try:
        if "\\" not in path:
            return jsonify({"error": "Invalid path format"}), 400

        key_name, subpath = path.split("\\", 1)

        if "\\" in subpath:
            parent_path, old_key_name = subpath.rsplit("\\", 1)
        else:
            parent_path = ""
            old_key_name = subpath

        main_key = getattr(winreg, key_name)
        print(parent_path)
        print(new_name)

        with winreg.OpenKey(main_key, parent_path, 0, winreg.KEY_READ | winreg.KEY_WRITE) as parent_key:
            with winreg.CreateKey(parent_key, new_name) as new_key:
                with winreg.OpenKey(parent_key, old_key_name, 0, winreg.KEY_READ) as old_key:
                    index = 0
                    while True:
                        try:
                            value_name, value_data, value_type = winreg.EnumValue(old_key, index)
                            winreg.SetValueEx(new_key, value_name, 0, value_type, value_data)
                            index += 1
                        except OSError:
                            break


                    index = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(old_key, index)
                            with winreg.OpenKey(old_key, subkey_name) as subkey:
                                with winreg.CreateKey(new_key, subkey_name) as new_subkey:
                                    copy_key_rec(subkey, new_subkey)
                            index += 1
                        except OSError:
                            break

            delete_key_rec(parent_key, old_key_name)

        return jsonify({"message": f"Key renamed to '{new_name}' successfully"}), 200

    except PermissionError:
        return jsonify({"error": f"Access denied for key {old_key_name}"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def copy_key_rec(old_key, new_key):
    index = 0
    while True:
        try:
            value_name, value_data, value_type = winreg.EnumValue(old_key, index)
            winreg.SetValueEx(new_key, value_name, 0, value_type, value_data)
            index += 1
        except OSError:
            break

    index = 0
    while True:
        try:
            subkey_name = winreg.EnumKey(old_key, index)
            with winreg.OpenKey(old_key, subkey_name) as subkey:
                with winreg.CreateKey(new_key, subkey_name) as new_subkey:
                    copy_key_rec(subkey, new_subkey)
            index += 1
        except OSError:
            break

def delete_key_rec(parent_key, key_name):
    try:
        with winreg.OpenKey(parent_key, key_name, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, 0)
                    delete_key_rec(key, subkey_name)

                except OSError:
                    break
        winreg.DeleteKey(parent_key, key_name)

    except Exception as e:
        print(f"Error deleting key {key_name}: {e}")
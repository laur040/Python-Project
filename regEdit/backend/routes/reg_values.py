from flask import Blueprint, jsonify, request
import winreg

register_val_bp = Blueprint("register_val", __name__)

@register_val_bp.route("/api/values", methods=["GET"])
def get_registry_values():
    path = request.args.get("path")
    if not path:
        return jsonify({"error": "No path specified"}), 400

    try:
        if "\\" not in path:
            key_name = path
            new_path = ""
        else:
            key_name, new_path = path.split("\\", 1)
        key = getattr(winreg, key_name)

        with winreg.OpenKey(key, new_path) as reg_key:

            values = []
            index = 0
            while True:
                try:
                    rez = winreg.EnumValue(reg_key, index)
                    value_name, value_val, value_type = rez
                    values.append({"name": value_name, "type": value_type, "value": value_val})
                    index += 1
                except OSError:
                    break

        if not values:
            values.append({"name": "(Default)", "type": "", "value": "No set value"})

        return jsonify(values)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@register_val_bp.route("/api/values", methods=["POST"])
def create_value():
    data = request.json
    path = data.get("path")
    name = data.get("name")
    content = data.get("content")
    type = data.get("type")

    val_type = {
        "REG_SZ": winreg.REG_SZ,
        "REG_DWORD": winreg.REG_DWORD,
        "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
        "REG_BINARY": winreg.REG_BINARY
    }

    type = val_type.get(type)
    if type is None:
        return jsonify({"error": f"Invalid type: {type}"}), 400

    try:
        if "\\" not in path:
            key_name = path
            subpath = ""
        else:
            key_name, subpath = path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        with winreg.OpenKey(main_key, subpath, 0, winreg.KEY_WRITE) as key:
            if type == winreg.REG_DWORD:
                content = int(content)

            winreg.SetValueEx(key, name, 1, type, content)

            return jsonify({"message": f"Value '{name}' created successfully"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@register_val_bp.route("/api/values", methods=["DELETE"])
def delete_value():
    data = request.json
    path = data.get("key")
    name = data.get("name")

    try:
        if "\\" not in path:
            key_name = path
            subpath = ""
        else:
            key_name, subpath = path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        with winreg.OpenKey(main_key, subpath, 0, winreg.KEY_WRITE) as key:
            winreg.DeleteValue(key, name)
            return jsonify({"message": f"Value '{name}' deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@register_val_bp.route("/api/values", methods=["PUT"])
def rename_value():
    data = request.json
    path = data.get("key")
    old_name = data.get("old_name")
    new_name = data.get("new_name")

    try:
        if "\\" not in path:
            key_name = path
            subpath = ""
        else:
            key_name, subpath = path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        with winreg.OpenKey(main_key, subpath, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            value_data, value_type = winreg.QueryValueEx(key, old_name)
            winreg.SetValueEx(key, new_name, 0, value_type, value_data)
            winreg.DeleteValue(key, old_name)

        return jsonify({"message": f"Value '{old_name}' renamed to '{new_name}' successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@register_val_bp.route("/api/values/edit", methods=["PUT"])
def edit_value():
    data = request.json
    path = data.get("key")
    val_name = data.get("val_name")
    new_data = data.get("new_data")

    try:
        if "\\" not in path:
            key_name = path
            subpath = ""
        else:
            key_name, subpath = path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        with winreg.OpenKey(main_key, subpath, 0, winreg.KEY_WRITE) as key:
            winreg.SetValueEx(key, val_name, 0, winreg.REG_SZ, new_data)


        return jsonify({"message": f"Value '{val_name}' updated to '{new_data}' successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@register_val_bp.route("/api/values/find", methods=["GET"])
def find_value():
    val_name = request.args.get("val_name")
    key_path = request.args.get("key")

    if not val_name or not key_path:
        return jsonify({"error": "Both 'val_name' and 'key' are required"}), 400

    try:
        if "\\" not in key_path:
            key_name = key_path
            subpath = ""
        else:
            key_name, subpath = key_path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        found_path = search_value_rec(main_key, subpath, val_name, key_name)
        if found_path:
            return jsonify({"message": f"Value '{val_name}' found in key: {found_path}", "path": found_path}), 200
        else:
            return jsonify({"error": f"Value '{val_name}' not found in key '{key_path}' or its subkeys"}), 404

    except PermissionError:
        return jsonify({"error": "Access denied"}), 403
    except Exception as e:
        return jsonify({"error": str(e)}), 500


def search_value_rec(parent_key, subpath, val_name, root_key_name):
    try:
        with winreg.OpenKey(parent_key, subpath, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    value_name, _, _ = winreg.EnumValue(key, index)
                    if value_name == val_name:
                        return f"{root_key_name}\\{subpath}" if subpath else root_key_name
                    index += 1
                except OSError:
                    break

            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, index)
                    next_subpath = f"{subpath}\\{subkey_name}" if subpath else subkey_name
                    found = search_value_rec(parent_key, next_subpath, val_name, root_key_name)
                    if found:
                        return found
                    index += 1
                except OSError:
                    break

    except PermissionError:
        print(f"Access denied to key: {subpath}. Skipping key")
        return None
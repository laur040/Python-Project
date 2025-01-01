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
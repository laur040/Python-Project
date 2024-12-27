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

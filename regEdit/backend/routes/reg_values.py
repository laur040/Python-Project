from flask import Blueprint, jsonify, request
import winreg

register_val_bp = Blueprint("register_val", __name__)

@register_val_bp.route("/api/values", methods=["GET"])
def get_registry_values():
    """
    HTTP GET endpoint to get all the values of a specified key.
    :return: (JSON) error message or the found values (name, type, value).
    """
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
                    if isinstance(value_val, bytes):
                        value_val = value_val.hex()
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
    """
    HTTP POST endpoint to create a new key.
    :return: (JSON) success or error message.
    """
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

    data_type = val_type.get(type)

    if data_type is None:
        return jsonify({"error": f"Invalid type: {data_type}"}), 400

    try:
        if data_type == winreg.REG_SZ:
            if not isinstance(content, str):
                return jsonify({"error": f"Content must be a string for type {type}"}), 400

        elif data_type == winreg.REG_DWORD:
            content = int(content)
            if not isinstance(content, int):
                return jsonify({"error": f"Content must be an integer for type {type}"}), 400

        elif data_type == winreg.REG_MULTI_SZ:
            if not isinstance(content, list) or not all(isinstance(item, str) for item in content):
                return jsonify({"error": f"Content must be a list of strings for type {type}"}), 400

        elif data_type == winreg.REG_BINARY:
            if isinstance(content, str):
                try:
                    content = bytes.fromhex(content.replace(" ", ""))
                except ValueError:
                    return jsonify({"error": f"Content is not a valid hex string for type {type}"}), 400

            elif not isinstance(content, bytes):
                return jsonify({"error": f"Content must be a bytes object for type {type}"}), 400

    except ValueError as e:
        return jsonify({"error": f"Invalid content format: {str(e)}"}), 400

    try:
        if "\\" not in path:
            key_name = path
            subpath = ""
        else:
            key_name, subpath = path.split("\\", 1)

        main_key = getattr(winreg, key_name)

        with winreg.OpenKey(main_key, subpath, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            index = 0
            while True:
                try:
                    value_name, _, _ = winreg.EnumValue(key, index)
                    if value_name == name:
                        return jsonify({"error": f"Value '{name}' already exists in the key '{path}'"}), 400
                    index += 1
                except OSError:
                    break

            winreg.SetValueEx(key, name, 1, data_type, content)
            return jsonify({"message": f"Value '{name}' created successfully"}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@register_val_bp.route("/api/values", methods=["DELETE"])
def delete_value():
    """
    HTTP DELETE endpoint to delete a value.
    :return: (JSON) success or error message.
    """
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
    """
    HTTP PUT endpoint to rename a value.
    :return: (JSON) success or error message.
    """
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
            index = 0
            while True:
                try:
                    value_name, _, _ = winreg.EnumValue(key, index)
                    if value_name == new_name:
                        return jsonify({"error": f"Value '{new_name}' already exists in the key '{path}'"}), 400
                    index += 1
                except OSError:
                    break

        with winreg.OpenKey(main_key, subpath, 0, winreg.KEY_READ | winreg.KEY_WRITE) as key:
            value_data, value_type = winreg.QueryValueEx(key, old_name)
            winreg.SetValueEx(key, new_name, 0, value_type, value_data)
            winreg.DeleteValue(key, old_name)

        return jsonify({"message": f"Value '{old_name}' renamed to '{new_name}' successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@register_val_bp.route("/api/values/edit", methods=["PUT"])
def edit_value():
    """
    HTTP PUT endpoint to edit the content of a value
    :return: (JSON) success or error message.
    """
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
    """
    HTTP GET endpoint to find a value name.
    :return: (JSON) success or error message.
    """
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


def search_value_rec(parent_key, subpath, val_name, parent_key_name):
    """
    Searches for a value name in a specified key and its subkeys.
    :param parent_key: the main key in which the specified key is located
    :param subpath: the path of the key that is searched in
    :param val_name: the name of the value that is searched
    :param parent_key_name: the name of the main key in which the specified key is located (necessary for building the correct path)
    :return: None if the value is not found. Otherwise, the full path to the found value
    """
    try:
        with winreg.OpenKey(parent_key, subpath, 0, winreg.KEY_READ) as key:
            index = 0
            while True:
                try:
                    value_name, _, _ = winreg.EnumValue(key, index)
                    if value_name == val_name:
                        return f"{parent_key_name}\\{subpath}" if subpath else parent_key_name
                    index += 1
                except OSError:
                    break

            index = 0
            while True:
                try:
                    subkey_name = winreg.EnumKey(key, index)
                    next_subpath = f"{subpath}\\{subkey_name}" if subpath else subkey_name
                    found = search_value_rec(parent_key, next_subpath, val_name, parent_key_name)
                    if found:
                        return found
                    index += 1
                except OSError:
                    break

    except PermissionError:
        print(f"Access denied to key: {subpath}. Skipping key")
        return None
from flask import Blueprint, jsonify, request
import winreg

register_bp = Blueprint("register", __name__)

def get_subkeys(path):
    subkeys = []
    return subkeys

@register_bp.route("/api/register", methods=["GET"])

def get_registry_subkeys():
    path = request.args.get("path")
    if not path:
        return jsonify({
            "HKEY_CLASSES_ROOT": [],
            "HKEY_CURRENT_USER": [],
            "HKEY_LOCAL_MACHINE": [],
            "HKEY_USERS": [],
            "HKEY_CURRENT_CONFIG": []
        })

    subkeys = get_subkeys(path)

    return jsonify({path: subkeys})
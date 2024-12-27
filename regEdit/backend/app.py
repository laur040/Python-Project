from flask import Flask, send_from_directory
from routes.get_all_registers import register_key_bp
from routes.get_values import register_val_bp

app = Flask(__name__)
app.register_blueprint(register_key_bp)
app.register_blueprint(register_val_bp)

@app.route('/home')
def home():
    return send_from_directory("../frontend", "home.html")




if __name__ == '__main__':
    app.run(host="127.0.0.1",debug = True)
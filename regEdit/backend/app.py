from flask import Flask, send_from_directory
from flask import render_template
from routes.reg_keys import register_key_bp
from routes.reg_values import register_val_bp

app = Flask(__name__, template_folder="../frontend/templates", static_folder="../frontend/static")
app.register_blueprint(register_key_bp)
app.register_blueprint(register_val_bp)

@app.route('/')
def home():
    return render_template("home.html")




if __name__ == '__main__':
    app.run(host="127.0.0.1",debug = True)
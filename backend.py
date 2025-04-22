from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import google.generativeai as genai
app = Flask(__name__)
CORS(app)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DB_LOCATION")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    if not all([name, email, password]):
        return jsonify({"error": "All fields are required."}), 400
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered."}), 409
    new_user = User(name=name, email=email, password=password)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({"message": "Registration successful!"}), 201
@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")
    user = User.query.filter_by(email=email).first()
    if user and user.password == password:
        return jsonify({"message": "Login successful!", "name": user.name}), 200
    return jsonify({"error": "Invalid email or password"}), 401
genai.configure(api_key=os.environ.get("GENAI_API_KEY"))
model = genai.GenerativeModel("gemma-3-27b-it")
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get("message", "")
    if not user_message:
        return jsonify({'response': "Please ask me something!"}), 400
    try:
        response = model.generate_content(user_message)
        return jsonify({'response': response.text.strip()})
    except Exception as e:
        print("Gemini API error:", e)
        return jsonify({'response': "Oops! Gemini had a problem. Try again soon."}), 500
with app.app_context():
    db.create_all()
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

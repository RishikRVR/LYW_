from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
import google.generativeai as genai

app = Flask(__name__)
CORS(app)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

# --- Required for SQLAlchemy bind-only setups ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'  # dummy fallback

# --- Get required env vars ---
USER_DB = os.environ.get("DB_LOCATION")
ADMIN_DB = os.environ.get("ADMIN_DB_LOCATION")
ADMIN_SECRET = os.environ.get("ADMIN_ACCESS_CODE")

if not USER_DB or not ADMIN_DB or not ADMIN_SECRET:
    raise RuntimeError("Missing one of the required environment variables: DB_LOCATION, ADMIN_DB_LOCATION, ADMIN_ACCESS_CODE")

app.config['SQLALCHEMY_BINDS'] = {
    'users': USER_DB,
    'admins': ADMIN_DB
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# --- Models ---
class User(db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

class Feedback(db.Model):
    __bind_key__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    user = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    reply = db.Column(db.Text)

class Admin(db.Model):
    __bind_key__ = 'admins'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

# --- User Auth ---
@app.route("/register", methods=["POST"])
def register_user():
    data = request.get_json()
    name, email, password = data.get("name"), data.get("email"), data.get("password")
    if not all([name, email, password]):
        return jsonify({"error": "All fields are required."}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409
    db.session.add(User(name=name, email=email, password=password))
    db.session.commit()
    return jsonify({"message": "Registration successful!"}), 201

@app.route("/login", methods=["POST"])
def login_user():
    data = request.get_json()
    email, password = data.get("email"), data.get("password")
    user = User.query.filter_by(email=email).first()
    if user and user.password == password:
        return jsonify({"message": "Login successful!", "name": user.name}), 200
    return jsonify({"error": "Invalid email or password"}), 401

# --- Admin Auth ---
@app.route("/admin_register", methods=["POST"])
def register_admin():
    data = request.get_json()
    name, email, password, secret = data.get("name"), data.get("email"), data.get("password"), data.get("secret")
    if secret != ADMIN_SECRET:
        return jsonify({"error": "Invalid secret code."}), 403
    if not all([name, email, password]):
        return jsonify({"error": "All fields are required."}), 400
    if Admin.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered."}), 409
    db.session.add(Admin(name=name, email=email, password=password))
    db.session.commit()
    return jsonify({"message": "Admin registered successfully!"}), 201

@app.route("/admin_login", methods=["POST"])
def login_admin():
    data = request.get_json()
    email, password = data.get("email"), data.get("password")
    admin = Admin.query.filter_by(email=email).first()
    if admin and admin.password == password:
        return jsonify({"message": "Login successful!", "name": admin.name}), 200
    return jsonify({"error": "Invalid email or password"}), 401

# --- Feedback ---
@app.route("/submit_feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json()
    user, message = data.get("user"), data.get("message")
    if not user or not message:
        return jsonify({"error": "User and message are required."}), 400
    db.session.add(Feedback(user=user, message=message))
    db.session.commit()
    return jsonify({"message": "Feedback submitted."}), 201

@app.route("/my_feedbacks", methods=["POST"])
def get_user_feedbacks():
    data = request.get_json()
    user = data.get("user")
    if not user:
        return jsonify({"error": "User not provided"}), 400
    feedbacks = Feedback.query.filter_by(user=user).all()
    return jsonify([{"id": f.id, "message": f.message, "reply": f.reply} for f in feedbacks])

@app.route("/feedbacks", methods=["GET"])
def list_feedbacks():
    feedbacks = Feedback.query.filter(Feedback.reply == None).all()  # <-- Only unreplied
    return jsonify([{"id": f.id, "user": f.user, "message": f.message} for f in feedbacks])

@app.route("/reply_feedback", methods=["POST"])
def reply_feedback():
    data = request.get_json()
    fid, reply = data.get("id"), data.get("reply")
    feedback = Feedback.query.get(fid)
    if feedback:
        feedback.reply = reply
        db.session.commit()
        return jsonify({"message": "Reply saved."})
    return jsonify({"error": "Feedback not found."}), 404

# --- Admin: Manage Users ---
@app.route("/users", methods=["GET"])
def list_users():
    users = User.query.all()
    return jsonify([{"name": u.name, "email": u.email} for u in users])

@app.route("/remove_user", methods=["POST"])
def remove_user():
    data = request.get_json()
    email = data.get("email")
    user = User.query.filter_by(email=email).first()
    if user:
        db.session.delete(user)
        db.session.commit()
        return jsonify({"message": "User removed."})
    return jsonify({"error": "User not found."}), 404

# --- Gemini Chat ---
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

# --- Init Databases ---
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True)

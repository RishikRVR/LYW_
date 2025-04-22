from flask import Flask, request, jsonify
from flask_cors import CORS
import google.generativeai as genai
import os
app = Flask(__name__)
CORS(app)
genai.configure(api_key="place_your_api_here")
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
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5011, debug=True)

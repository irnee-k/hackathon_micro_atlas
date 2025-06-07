# test_flask_app.py

from flask import Flask

app = Flask(__name__)

@app.route("/")
def hello_world():
    return "<p>Hello, World! Flask is working!</p>"

if __name__ == "__main__":
    print("Starting Flask test server on http://localhost:5001")
    app.run(port=5001, debug=True)
from flask import Flask, render_template, request
app = Flask(__name__)
import os
from os.path import join, dirname
from dotenv import load_dotenv
from pymongo import MongoClient
# pip install python-dotenv pymongo
# make folder .env for credential
# MONGODB_CONNECTION_STRING = your string

dotenv_path = join(dirname(__file__),'.env')
load_dotenv(dotenv_path)
MONGODB_CONNECTION_STRING = os.environ.get('MONGODB_CONNECTION_STRING')
client = MongoClient(MONGODB_CONNECTION_STRING)
db = client.dbname



@app.route('/')
def landingpage():
    return render_template('index.html')


if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
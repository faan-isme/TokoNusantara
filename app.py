import os
from os.path import join, dirname
from dotenv import load_dotenv
from pymongo import MongoClient
import jwt
import datetime
import hashlib
from flask import Flask, render_template, jsonify, request, redirect, url_for, make_response, session
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta

app = Flask(__name__)
dotenv_path = join(dirname(__file__),'.env')
load_dotenv(dotenv_path)
SECRET_KEY = os.environ.get('SECRET_KEY')
MONGODB_CONNECTION_STRING = os.environ.get('MONGODB_CONNECTION_STRING')
client = MongoClient(MONGODB_CONNECTION_STRING)
db = client.toknus

# route landing page
@app.route('/')
def landingpage():
    return render_template('index.html')

# route login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email_receive = request.form["email"]
        password_receive = request.form["password"]
        pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
        result = db.users.find_one(
            {
                "email": email_receive,
                "password": pw_hash,
            }
        )
        if result:
            role = result.get('role')
            payload = {
                "id": email_receive,
                "role": role,
                # the token will be valid for 24 hours
                "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
            }
            token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
            response = make_response(redirect(url_for('home')))
            response.set_cookie('token', token)
            return response
        else:
            msg = 'Email dan Password tidak cocok!'
            return render_template('login.html', msg=msg)
    else:
        msg = request.args.get('msg')
        return render_template('login.html', msg=msg)

# route register
@app.route("/register", methods=["POST"])
def register():
    username_receive = request.form.get('username')
    toserbaname_receive = request.form.get('toserbaname')
    email_receive = request.form['email']
    password_receive = request.form['password']
    # jika register sebagai custommer
    if username_receive:
        password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
        doc = {
            "username": username_receive,                               # id
            "email": email_receive,                                     # email
            "password": password_hash,                                  # password
            "role": "customer",                                         # role
            "profile_pic": "",                                          # profile image file name
            "profile_pic_real": "profile_pics/profile_placeholder.png", # a default profile image
            "profile_info": ""                                          # a profile description
        }
        db.users.insert_one(doc)
        response = make_response(redirect(url_for('login',msg='Registrasi Berhasil')))
        return response
    # jika register sebagai seller
    elif toserbaname_receive:
        password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
        doc = {
            "toserbaname": toserbaname_receive,                         # id
            "email": email_receive,                                     # email
            "password": password_hash,                                  # password
            "role": "seller",                                           # role
            "profile_pic": "",                                          # profile image file name
            "profile_pic_real": "profile_pics/profile_placeholder.png", # a default profile image
            "profile_info": ""                                          # a profile description
        }
        db.users.insert_one(doc)
        response = make_response(redirect(url_for('login',msg='Registrasi Berhasil')))
        return response
    else:
        return redirect(url_for('login',msg='Terjadi kesalahan saat registrasi'))
    
# route home
@app.route('/home')
def home():
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        if user_role == 'customer':
            return render_template('homeCustomer.html')
        elif user_role == 'seller':
            return render_template('homeSeller.html')
        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
        
    
        



    

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
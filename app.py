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
from bson import ObjectId

# Set the directories for uploaded photos
USER_UPLOAD_FOLDER = 'static/profile_pics'
PRODUCT_UPLOAD_FOLDER = 'static/foto_produk'

app = Flask(__name__)
# dotenv_path = join(dirname(__file__),'.env')
# load_dotenv(dotenv_path)
# SECRET_KEY = os.environ.get('SECRET_KEY')
# MONGODB_CONNECTION_STRING = os.environ.get('MONGODB_CONNECTION_STRING')

SECRET_KEY='manjaro'
MONGODB_CONNECTION_STRING='mongodb+srv://tokonusantara:manjaro@cluster0.5s9mqty.mongodb.net/?retryWrites=true&w=majority'

client = MongoClient(MONGODB_CONNECTION_STRING)
db = client.toknus

# route landing page
@app.route('/')
def landingpage():
    return render_template('index.html')
# route logout
@app.route('/logout')
def logout():
    response = make_response(redirect(url_for('landingpage')))
    response.delete_cookie('token')
    return response
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
            id = str(result.get('_id'))
            payload = {
                "id": id,
                "role": role,
                # the token will be valid for 24 hours
                "exp": datetime.utcnow() + timedelta(seconds=60 * 60 * 24),
            }
            if role == 'customer':
                payload['username'] = result.get('username')
            elif role == 'seller':
                payload['toserbaname'] = result.get('toserbaname') 
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
    # cek email
    exists = bool(db.users.find_one({"email": email_receive}))
    if exists:
        response = make_response(redirect(url_for('login',msg='Email telah digunakan!')))
        return response
    # jika register sebagai custommer
    if username_receive:
        password_hash = hashlib.sha256(password_receive.encode('utf-8')).hexdigest()
        doc = {
            "username": username_receive,                               # id
            "email": email_receive,                                     # email
            "password": password_hash,                                  # password
            "no_telp":"",                                               # nomor telepon
            "alamat":"",                                                # alamat
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
            "no_telp":"",                                               # nomor telepon
            "alamat":"",                                                # alamat
            "role": "seller",                                           # role
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
            return render_template('homeCustomer.html', username=payload['username'])
        elif user_role == 'seller':
            # Mengambil data produk dari DB
            products = db.produk.find({"toserbaname": payload['toserbaname']})
            return render_template('homeSeller2.html', toserbaname=payload['toserbaname'], products=products)
        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
        
@app.route('/profile')
def profile():
    token_receive = request.cookies.get('token')
    msg = request.args.get('msg')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        # ambil data user & data barang
        # data['jml']= db.stok.count()
        # data['stok'] = db.stok.find()
        id_obj = ObjectId(payload['id'])
        data = db.users.find_one({'_id': id_obj})
        user_role = payload['role']
        if user_role == 'customer':
            return render_template('profileCustomer.html',data=data,msg=msg)
        elif user_role == 'seller':
            return render_template('profileSeller.html',data=data,msg=msg)
        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
        
@app.route('/profile/edit', methods=['POST'])
def editProfile():
    token_receive = request.cookies.get('token')
    # ambil data form
    username_receive = request.form.get('username')
    toserbaname_receive = request.form.get('toserbaname') 
    email_receive = request.form['email']
    password_receive = request.form.get('password')
    newPassword_receive = request.form.get('newPassword')
    alamat_receive = request.form.get('alamat')
    noTelp_receive = request.form.get('no_telp')
    profile_receive = request.files.get('foto')
    desc_receive = request.form.get('desc')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        user_id = payload['id']
        id_obj = ObjectId(user_id)
        # kondisi jika password diterima/ganti password
        if password_receive:
            # otentikasi
            pw_hash = hashlib.sha256(password_receive.encode("utf-8")).hexdigest()
            result = db.users.find_one(
                {
                    "_id": id_obj,
                    "password": pw_hash,
                }
            )
            # hash pw baru
            newPassword_receive = hashlib.sha256(newPassword_receive.encode("utf-8")).hexdigest()
            # otentikasi berhasil
            if result:
                # cek role
                if user_role == 'customer':
                    new_doc={
                        'username':username_receive,
                        'email':email_receive,
                        'password':newPassword_receive,
                        'profile_info':desc_receive,
                        'no_telp':noTelp_receive,                                               
                        'alamat':alamat_receive,
                    }
                    if profile_receive:
                        uploadfoto(profile_receive,user_id,new_doc)
                        db.users.update_one({'_id':id_obj},{'$set':new_doc})
                        response = make_response(redirect(url_for('profile',msg='Update data dan password berhasil')))
                        return response
                    else:
                        db.users.update_one({'_id':id_obj},{'$set':new_doc})
                        response = make_response(redirect(url_for('profile',msg='Update data dan password berhasil')))
                        return response
                else :
                    new_doc={
                            'toserbaname':toserbaname_receive,
                            'email':email_receive,
                            'password':newPassword_receive,
                            'profile_info':desc_receive,
                            'no_telp':noTelp_receive,                                               
                            'alamat':alamat_receive,
                    }
                    if profile_receive:
                        uploadfoto(profile_receive,user_id,new_doc)
                        db.users.update_one({'_id':id_obj},{'$set':new_doc})
                        response = make_response(redirect(url_for('profile',msg='Update data dan password berhasil')))
                        return response
                    else:
                        db.users.update_one({'_id':id_obj},{'$set':new_doc})
                        response = make_response(redirect(url_for('profile',msg='Update data dan password berhasil')))
                        return response
                        
            # outentikasi gagal
            else:
                response = make_response(redirect(url_for('profile',msg='password tidak cocok')))
                return response
            
        else:
            
            if user_role == 'customer':
                new_doc={
                    'username':username_receive,
                    'email':email_receive,
                    'profile_info':desc_receive,
                    'no_telp':noTelp_receive,                                               
                    'alamat':alamat_receive,
                }
                if profile_receive:
                    uploadfoto(profile_receive,user_id,new_doc)
                    db.users.update_one({'_id':id_obj},{'$set':new_doc})
                    response = make_response(redirect(url_for('profile',msg='Update data berhasil')))
                    return response
                else:
                    db.users.update_one({'_id':id_obj},{'$set':new_doc})
                    response = make_response(redirect(url_for('profile',msg='Update data berhasil')))
                    return response
            else :
                new_doc={
                'toserbaname':toserbaname_receive,
                'email':email_receive,
                'profile_info':desc_receive,
                'no_telp':noTelp_receive,                                               
                'alamat':alamat_receive,
                }                
                if profile_receive:
                    uploadfoto(profile_receive,user_id,new_doc)
                    db.users.update_one({'_id':id_obj},{'$set':new_doc})
                    response = make_response(redirect(url_for('profile',msg='Update data berhasil')))
                    return response
                else:
                    db.users.update_one({'_id':id_obj},{'$set':new_doc})
                    response = make_response(redirect(url_for('profile',msg='Update data berhasil')))
                    return response
      
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
    
# fungsi update foto
def uploadfoto(profile_receive,user_id,new_doc):
    filename = secure_filename(profile_receive.filename)
    extension = filename.split(".")[-1]
    file_path = f"profile_pics/{user_id}.{extension}"

    profile_receive.save("./static/" + file_path)
    new_doc["profile_pic_real"] = file_path
    return new_doc

def upload_product_photo(product_photo, product_id):
    filename = secure_filename(product_photo.filename)
    extension = filename.split(".")[-1]
    file_path = os.path.join("static", "foto_produk", f"{product_id}.{extension}")

    product_photo.save("./static/" + file_path)
    return file_path

# route to handle the insertion of data into the "produk" collection
@app.route('/post_produk', methods=['POST'])
def post_produk():
    try:
        data = request.get_json()

        product_photo = request.files.get('product_photo')

        if product_photo:
            product_id = data.get('product_id')
            data['product_photo'] = upload_product_photo(product_photo, product_id)
        # Insert data into the "produk" collection
        db.produk.insert_one(data)

        return jsonify({"success": True, "message": "Data posted successfully"})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/sidebar')
def sidebar():
    return render_template('sidebar.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
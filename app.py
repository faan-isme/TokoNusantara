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
import shortuuid


# Set the directories for uploaded photos
USER_UPLOAD_FOLDER = 'static/profile_pics'
PRODUCT_UPLOAD_FOLDER = 'static/foto_produk'

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
    msg = request.args.get('msg')
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        user_id = payload['id']
        
        if user_role == 'customer':
            data = db.users.find({'customer_id': user_id})
            return render_template('index.html', username=payload['username'])
        elif user_role == 'seller':
            data = db.produk.find({'seller_id':user_id})
            return render_template('seller/homeSeller.html',data=data, msg=msg)

        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))

    # apabila tidak ada login, hanya memuat laman tanpa payload
    return render_template('index.html', msg=msg)
    
#route profile 
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

# route edit profile
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
    profile_receive = request.files.get('foto-prof')
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
                        old_foto = db.users.find_one({'_id':id_obj})
                        old_foto = old_foto.get('profile_pic_real')
                        if old_foto != "profile_pics/profile_placeholder.png":
                            old_foto = f'./static/'+ old_foto
                            os.remove(old_foto)
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
                        old_foto = db.users.find_one({'_id':id_obj})
                        old_foto = old_foto.get('profile_pic_real')
                        if old_foto != "profile_pics/profile_placeholder.png":
                            old_foto = f'./static/'+ old_foto
                            os.remove(old_foto)
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
                    old_foto = db.users.find_one({'_id':id_obj})
                    old_foto = old_foto.get('profile_pic_real')
                    if old_foto != "profile_pics/profile_placeholder.png":
                        old_foto = f'./static/'+ old_foto
                        os.remove(old_foto)
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
                    old_foto = db.users.find_one({'_id':id_obj})
                    old_foto = old_foto.get('profile_pic_real')
                    if old_foto != "profile_pics/profile_placeholder.png":
                        old_foto = f'./static/'+ old_foto
                        os.remove(old_foto)
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
# get produk seller
@app.route('/get_products', methods=['GET'])
def get_products():
    kategori = request.args.get('category')
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        user_id = payload['id']
        
        if user_role == 'seller':
            if kategori== 'Semua':
                posts = list(db.produk.find({'seller_id':user_id}))
                for post in posts:
                    post["_id"]=str(post["_id"])
                return jsonify(
                    {
                        "result": "success",
                        "posts": posts
                        
                    }
                )
            else:
                posts = list(db.produk.find({'seller_id':user_id, 'kategori':kategori}))
                for post in posts:
                    post["_id"]=str(post["_id"])
                return jsonify(
                    {
                        "result": "success",
                        "posts": posts
                        
                    }
                )
        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))


# route jual
@app.route('/jual', methods=['POST'])
def jual():
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        user_id=payload['id']
        if user_role == 'seller':
            data_list = request.json
            for item in data_list:
                
                id_obj =ObjectId(item['id'])
                result = db.produk.find_one({'_id':id_obj})
                if not result:
                    return jsonify(
                        {
                            "result": "fail",
                            
                        }
                    )
            # buat perulangan, ambil key id, cocokan dengan barang di db, update jumlah
            for item in data_list:
                # tambahkan id barang
                nama= item['nama']
                jumlah= int(item['jumlah'])
                tanggal= item['tanggal']
                id_obj =ObjectId(item['id'])
                # cari jumlah produk
                produk = db.produk.find_one({'_id':id_obj})
                stok =int(produk.get('jumlah'))
                # update stok
                updatestok = str(stok-jumlah)
                db.produk.update_one({'_id':id_obj},{'$set':{'jumlah': updatestok}})
                # masukkan ke hostori transaksi
                doc ={
                    'tanggal':tanggal,
                    'namaBarang':nama,
                    'jumlah':jumlah,
                    'seller_id':user_id
                }
                db.histori.insert_one(doc)
            
            
            return jsonify(
                {
                    "result": "success",
                    
                }
            )

        else:
            return redirect(url_for('home',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
        

    
# input produk
@app.route('/inputBarang', methods=['POST'])
def inputBarang():
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        seller_id=payload['id']
        toserbaname = payload['toserbaname']
        if user_role == 'seller':
            namaBarang = request.form['namaBarang']
            kategori = request.form['kategori']
            jumlah = request.form['jumlah']
            harga = request.form['harga']
            foto = request.files['foto']
            desc = request.form['desc']
            
            filename = secure_filename(foto.filename)
            extension = filename.split(".")[-1]
            uniqename=shortuuid.uuid()
            file_path = f"foto_produk/{uniqename}.{extension}"
            foto.save("./static/" + file_path)
            doc={
                'namaBarang':namaBarang,
                'kategori':kategori,
                'jumlah':jumlah,
                'harga':harga,
                'desc':desc,
                'foto':file_path,
                'seller_id':seller_id,
                'toserbaname':toserbaname
            }
            db.produk.insert_one(doc)
            return redirect(url_for('home',msg='Input barang berhasil!')) 
        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
# route update stok
@app.route('/updateJml', methods=['POST'])
def updateJml():
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        if user_role == 'seller':
            jumlah = request.form['jumlah']
            id = request.form['id'] 
            id_obj =ObjectId(id)
            result = db.produk.find_one({'_id':id_obj})
            if not result:
                return jsonify(
                    {
                        "result": "fail",
                        
                    }
                )
            # tambahkan id barang
            
            jumlah= int(jumlah)
            
            # cari jumlah produk
            stok =int(result.get('jumlah'))
            # update stok
            updatestok = str(stok+jumlah)
            db.produk.update_one({'_id':id_obj},{'$set':{'jumlah': updatestok}})         
            
            return jsonify(
                {
                    "result": "success",
                    
                }
            )

        else:
            return redirect(url_for('home',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))


@app.route('/sidebar')
def sidebar():
    return render_template('sidebar.html')

#route dashboard  
@app.route('/dashboard')
def dashboard():
    msg = request.args.get('msg')
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        user_id = payload['id']
        
        if user_role == 'seller':
            data = db.produk.find({'seller_id':user_id})
            histori = db.histori.find({'seller_id':user_id})
            return render_template('seller/dashboard.html',data=data,histori=histori, msg=msg)
        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
    
# route update produk
@app.route('/produk/update', methods=['POST'])
def updateBarang():
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        if user_role == 'seller':
            namaBarang = request.form['namaBarang']
            kategori = request.form['kategori']
            jumlah = request.form['jumlah']
            harga = request.form['harga']
            foto = request.files.get('foto')
            desc = request.form['desc']
            id = request.form['id_barang_update']
            id_obj=ObjectId(id)
            
            result = db.produk.find_one({'_id':id_obj})
            if result:
                if foto:
                    
                    # simpan foto baru
                    filename = secure_filename(foto.filename)
                    extension = filename.split(".")[-1]
                    uniqename=shortuuid.uuid()
                    file_path = f"foto_produk/{uniqename}.{extension}"
                    foto.save("./static/" + file_path)
                    # hapus foto lama
                    old_foto = result.get('foto')
                    old_foto = f'./static/'+ old_foto
                    os.remove(old_foto)
                    
                    doc={
                        'namaBarang':namaBarang,
                        'kategori':kategori,
                        'jumlah':jumlah,
                        'harga':harga,
                        'desc':desc,
                        'foto':file_path,
                        
                    }
                    db.produk.update_one({'_id':id_obj},{'$set':doc})
                    return redirect(url_for('dashboard',msg='Edit barang berhasil!'))
                else:
                    doc={
                        'namaBarang':namaBarang,
                        'kategori':kategori,
                        'jumlah':jumlah,
                        'harga':harga,
                        'desc':desc,
                        
                    }
                    db.produk.update_one({'_id':id_obj},{'$set':doc})
                    return redirect(url_for('dashboard',msg='Edit barang berhasil!'))     
            else:
                 return redirect(url_for('dashboard',msg='Produk Tidak di temukan!'))
        else:
            return redirect(url_for('login',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
    
# route hapus produk
@app.route('/produk/hapus', methods=['POST'])
def hapusproduk():
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        if user_role == 'seller':
            id = request.form['id'] 
            id_obj =ObjectId(id)
            result = db.produk.find_one({'_id':id_obj})
            if not result:
                return jsonify(
                    {
                        "result": "fail",
                        
                    }
                )
           
            
            db.produk.delete_one( { "_id": id_obj} )       
            
            return jsonify(
                {
                    "result": "success",
                    
                }
            )

        else:
            return redirect(url_for('home',msg='Role tidak sesuai!'))   
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="Token telah kadaluarsa"))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="Terjadi masalah saat login"))
    
# route hapus histori
@app.route('/histori/hapus', methods=['POST'])
def hapushistori():
    token_receive = request.cookies.get('token')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        user_role = payload['role']
        if user_role == 'seller':
            id = request.form['id']
            id_obj =ObjectId(id)
            result = db.histori.find_one({'_id':id_obj})
            if not result:
                return jsonify(
                    {
                        "result": "fail",
                        
                    }
                )
           
            
            db.histori.delete_one( { "_id": id_obj} )       
            
            return jsonify(
                {
                    "result": "success",
                    
                }
            )

        else:
            return redirect(url_for('home',msg='Role tidak sesuai!'))   
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

# 16 Dec, utk mendisplay semua seller, pada laman home, baik visitor maupun sbg logged in customer
# Add this route to get the list of sellers
@app.route('/get_sellers', methods=['GET'])
def get_sellers():
    try:
        # Fetch sellers from the database
        sellers = db.users.find({"role": "seller"})
        seller_list = []

        # Create a list of seller details
        for seller in sellers:
            seller_details = {
                "toserbaname": seller.get("toserbaname"),
                "profile_info": seller.get("profile_info"),
                "no_telp": seller.get("no_telp"),
                "alamat": seller.get("alamat"),
                "profile_pic_real": seller.get("profile_pic_real")
            }
            seller_list.append(seller_details)

        return jsonify({"success": True, "sellers": seller_list})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@app.route('/get_produk', methods=['GET'])
def get_produk():
    try:
        # Fetch sellers from the database
         # Mengambil data produk dari DB
        produks = db.produk.find()
        produk_list = []
        
        # Create a list of seller details
        for produk in produks:
            produk_details = {
                "namaBarang": produk.get("namaBarang"),
                "jumlah": produk.get("jumlah"),
                "harga": produk.get("harga"),
                "desc": produk.get("desc"),
                "toserbaname": produk.get("toserbaname"),
                "foto": produk.get("foto"),  
                "kategori": produk.get("kategori")
            }

            
            produk_list.append(produk_details)

        return jsonify({"success": True, "produk_list": produk_list})

    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_produk route: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/user/<toserbaname>')
def seller_profile(toserbaname):
    try:
        # Fetch seller data based on toserbaname from the database
        seller = db.users.find_one({"toserbaname": toserbaname, "role": "seller"})
        
        if seller:
            # Extract necessary details from the seller data
            username = seller.get("username", "No Username")
            seller_id = seller.get("_id")

            # Fetch products associated with the seller's toserbaname
            products = db.produk.find({"seller_id": str(seller_id)})

            # Render the seller profile page with the fetched data
            return render_template('profileSeller_customerView.html', toserbaname=toserbaname, username=username, data=seller, products=products)
        else:
            # Handle case where seller not found
            return render_template('profileSeller_customerView.html', toserbaname=toserbaname, username="No Username", data=None, products=[])
    except Exception as e:
        # Log the error for debugging
        print(f"Error in seller_profile route: {e}")
        return render_template('error.html', error_message="An error occurred while fetching seller profile.")

@app.route('/add_to_mylist', methods=['POST'])
def add_to_mylist():
    try:
        # Get the JSON data from the request
        data = request.json

        # Extract relevant information from the JSON data
        username = data.get('username')
        namaProduk = data.get('namaProduk')
        harga = data.get('harga')
        toserbaname = data.get('toserbaname')

        mylist_doc = {
            'username': username,
            'namaProduk': namaProduk,
            'harga': harga,
            'toserbaname': toserbaname
        }
        db.mylist.insert_one(mylist_doc)

        # Return a success response to the client
        return jsonify({"success": True, "message": "Product added to MyList successfully"})
    
    except Exception as e:
        # Log the error for debugging
        print(f"Error in add_to_mylist route: {e}")
        return jsonify({"success": False, "message": str(e)})

@app.route('/get_mylist', methods=['GET'])
def get_mylist():
    try:
        # Get the currently logged-in user's username from the JWT token
        token_receive = request.cookies.get('token')
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=["HS256"])
        username = payload.get('username')

        # Fetch mylist data for the logged-in user from the database
        mylist_data = db.mylist.find({'username': username})

        # Create a list to store mylist items
        mylist_items = []

        # Iterate through mylist data and extract relevant information
        for item in mylist_data:
            mylist_item = {
                'username': item.get('username'),
                'namaProduk': item.get('namaProduk'),
                'harga': item.get('harga'),
                'toserbaname': item.get('toserbaname')
            }
            mylist_items.append(mylist_item)

        # Return the mylist data as a JSON response
        return jsonify({"success": True, "mylist_items": mylist_items})
    
    except jwt.ExpiredSignatureError:
        return jsonify({"success": False, "message": "Token has expired"})
    except jwt.exceptions.DecodeError:
        return jsonify({"success": False, "message": "Error decoding token"})
    except Exception as e:
        # Log the error for debugging
        print(f"Error in get_mylist route: {e}")
        return jsonify({"success": False, "message": str(e)})

if __name__ == "__main__":
    app.run("0.0.0.0", port=5000, debug=True)
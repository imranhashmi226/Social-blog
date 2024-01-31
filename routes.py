# Standard library imports
from datetime import datetime
import csv
import os
import pathlib
from urllib import request

# Related third party imports
from bson.objectid import ObjectId
from flask import render_template, url_for, request, flash, redirect, session, abort
from flask_mail import Message
from flask_paginate import Pagination, get_page_parameter
from google_auth_oauthlib.flow import Flow
from google.oauth2 import id_token
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer
from transformers import pipeline
import google.auth.transport.requests
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem.porter import PorterStemmer
import pwnedpasswords
import requests
from pip._vendor import cachecontrol

# Local application/library specific imports
from __main__ import app
from app import bcrypt, db, postdb, mail

# Initialize PorterStemmer
porter = PorterStemmer()

GOOGLE_CLIENT_ID = ""
client_secrets_file = os.path.join(pathlib.Path(__file__).parent, "client_secret.json")
flow = Flow.from_client_secrets_file(
    client_secrets_file=client_secrets_file,
    scopes=["https://www.googleapis.com/auth/userinfo.profile", "https://www.googleapis.com/auth/userinfo.email", "openid"],
    redirect_uri="http://127.0.0.1:5000/callback"
)


app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = ''
app.config['MAIL_PASSWORD'] = ''





import smtplib, ssl
port = 587
# # port = 465
smtp_server = "smtp.gmail.com"



@app.route('/', methods=['GET'])
def home():
    PER_PAGE = 3
    page = request.args.get(get_page_parameter(), type=int, default=1)
    data = postdb.find({}).sort('date_posted',-1)
    # datacnt = postdb.count_documents({})
    # print(datacnt)
    # pagination = Pagination(page=page, total=data.count_documents(),per_page=3, record_name='posts')
    posts=[]
    for i in data:
        posts.append(i)
    i=(page-1)*PER_PAGE
    pposts=posts[i:i+3]
    pagination = Pagination(page=page, total=len(posts),per_page=PER_PAGE, record_name='posts')
    return render_template("demo.html",posts=pposts,pagination=pagination)

@app.route('/login', methods=['GET','POST'])
def logion():
    if request.method=='POST':
       email = request.form['email']
       password = request.form['password']
       userpassword = db.find_one({'email':email},{'_id':0})
       if userpassword is not None and bcrypt.check_password_hash(userpassword['password'],password):
        session["email"] = email
        flash(f'User logged in successfully','success')
        return redirect(url_for('home'))
       else:
        flash(f'Invalid Credentials','danger')
        return redirect(url_for('logion'))

    return render_template("signin.html")


@app.route('/signup', methods=['GET','POST'])
def signup():
    if request.method=='POST':
        name = request.form['name']
        email= request.form['email']
        password = request.form['password']
        count = pwnedpasswords.check(password)
        if(count>1000):
            flash(f'Use Strong Password, Compromised more than 1000 times.','danger')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            if ((db.count_documents({'email':email}))!=0):
                flash(f'Email Id already exists','danger')
            else:
                id = db.insert_one({
            'name':name,
            'email':email,
            'password':hashed_password
                })
                flash(f'User {name} is succesfully created','success')
                return redirect(url_for('logion'))

    return render_template("signup.html")



@app.route("/logout")
def logout():
    session["email"] = None
    session['state'] = None
    session.clear()
    return redirect("/")


@app.route("/post/new",methods=['GET','POST'])
def new_post():
    if request.method=='POST':
        if session['email'] is None:
            return redirect(url_for('logion'))
        else:
            title= request.form['title']
            description = request.form['description']

            tokens = word_tokenize(description.lower())
            # Remove stop words
            english_stopwords = stopwords.words('english')
            tokens_wo_stopwords = [t for t in tokens if t not in english_stopwords]
            stem_data = [porter.stem(word) for word in tokens_wo_stopwords]
            cnt=0
            with open('bad-words.csv', newline='') as csvfile:
                csvdata = csv.reader(csvfile, delimiter=' ', quotechar='|')
                for row in csvdata:
                    for i in stem_data:
                        if(i in row):
                            cnt = cnt+1
            if(cnt>0):
                flash(f'Post contains abusive words. Kindly use respected words.','warning')
            else:
                uemail= session["email"]
                user = db.find_one({'email':uemail},{'_id':0,'name':1})
                username = user['name']
                if username is None:
                    username= session['name']
                id = postdb.insert_one({'email':uemail,'name':username,'title':title,
                        'description':description,'date_posted':datetime.now()})
                flash('Post created succesfully','success')
                return redirect(url_for('home'))
    
    if session['email'] is None:
        return redirect(url_for('logion'))
    else:
        return render_template("create_post.html") 
        


@app.route("/post/<id>",methods=['GET','POST'])
def post(id):
    dpost = postdb.find({'_id':ObjectId(id)})
    posts=[]
    for i in dpost:
        posts.append(i)
    return render_template("post.html",posts=posts)

@app.route("/delete_post/<id>",methods=['GET','POST'])
def delete_post(id):
    postmail = postdb.find({'_id':ObjectId(id)},{'_id':0,'email':1})
    for i in postmail:
        pmail= i
    
    if session['email'] is None:
        return redirect(url_for('logion'))
    if session['email'] !=pmail['email']:
        flash(f'You are not authorized','danger')
        return redirect(url_for('home'))
    else:
        postdb.delete_one({'_id':ObjectId(id)})
        flash('Post deleted succesfully','success')
        return redirect(url_for('home'))

@app.route("/update_post/<id>",methods=['GET','POST'])
def update_post(id):
    postmail = postdb.find({'_id':ObjectId(id)},{'_id':0,'email':1})
    for i in postmail:
        pmail= i
    if session['email'] is None:
        return redirect(url_for('logion'))
    if session['email'] !=pmail['email']:
        flash(f'You are not authorized','danger')
        return redirect(url_for('home'))
    else:
        if request.method=='GET':
            update = postdb.find({'_id':ObjectId(id)})
            oldvalues = []
            for i in update:
                oldvalues.append(i)
        if request.method=='POST':
            title= request.form['title']
            description = request.form['description']
            uemail= session["email"]

            tokens = word_tokenize(description.lower())
            # Remove stop words
            english_stopwords = stopwords.words('english')
            tokens_wo_stopwords = [t for t in tokens if t not in english_stopwords]
            stem_data = [porter.stem(word) for word in tokens_wo_stopwords]
            cnt=0
            with open('bad-words.csv', newline='') as csvfile:
                csvdata = csv.reader(csvfile, delimiter=' ', quotechar='|')
                for row in csvdata:
                    for i in stem_data:
                        if(i in row):
                            cnt = cnt+1
            if(cnt>0):
                flash(f'Post contains abusive words. Kindly use respected words.','warning')
                return redirect(url_for('update_post',id=id))

            user = db.find_one({'email':uemail},{'_id':0,'name':1})
            username = user['name']
            postdb.delete_many({'_id':ObjectId(id)})
            id = postdb.insert_one({'email':uemail,'name':username,'title':title,
                'description':description,'date_posted':datetime.now()})
            flash('Post updated succesfully','success')
            return redirect(url_for('home'))
    return render_template("updatepost.html",posts=oldvalues)

@app.route("/users_post",methods=['GET','POST'])
def users_post():
    if session['email'] is None:
        return redirect(url_for('logion'))
    else:
        uemail = session['email']
        data = postdb.find({'email':uemail}).sort('date_posted',-1)
        posts=[]
        for i in data:
            posts.append(i)
    return render_template("users_posts.html",posts=posts)

@app.route("/generate_post",methods=['GET','POST'])
def generate_post():
    # Creating a TextGenerationPipeline for text generation
    generator = pipeline(task='text-generation', model='gpt2')
    # Generating
    data= generator("writing a post about GPT-2 machine learning model", max_length=150, num_return_sequences=3)
    print(data)
    return redirect(url_for('home'))








# def get_reset_token(self, expires_sec=1800):
#     s = Serializer(app.config['SECRET_KEY'], expires_sec)
#     return s.dumps({'email': self.id}).decode('utf-8')

# @staticmethod
# def verify_reset_token(token):
#     s = Serializer(app.config['SECRET_KEY'])
#     try:
#         email = s.loads(token)['email']
#     except:
#         return None
#     return session['email']


# def send_reset_email(user):
#     print(user)
#     s = Serializer(app.config['SECRET_KEY'], 1800)
#     token  = s.dumps({'email': user}).decode('utf-8')
#     msg = Message('Password Reset Request',
#                   sender='immu@icorestack.io',
#                   recipients=[user])
#     msg.body = f'''To reset your password, visit the following link:
# {url_for('reset_token', token=token, _external=True)}
# If you did not make this request then simply ignore this email and no changes will be made.
# '''
#     mail.send(msg)

    # receiver_email = user
    # message = token
    # context = ssl.create_default_context()
    # with smtplib.SMTP(smtp_server, port) as server:
    #     server.ehlo()  # Can be omitted
    #     server.starttls(context=context)
    #     server.ehlo()  # Can be omitted
    #     server.login(sender_email, password)
    #     server.sendmail(sender_email, receiver_email, message)
    #     flash(f'mail sent','success')

# @app.route("/reset_password", methods=['GET', 'POST'])
# def reset_request():
#     sender_email = 'imran.hashmi226@gmail.com'
#     senderpassword = 'wjeovbiumczcvnpf'
#     if request.method=='POST':
#         email= request.form['mail']
#         user = db.find_one({'email':email},{'_id':0,'email':1})
#         if user is not None:
#             s = Serializer(app.config['SECRET_KEY'], 1800)
#             token  = s.dumps({'email': user['email']}).decode('utf-8')
#             receiver_email = user['email']
#             # message = {url_for('reset_token', token=token, _external=True)}
#             message=token
#             context = ssl.create_default_context()
#             with smtplib.SMTP(smtp_server, port) as server:
#                 server.ehlo()  # Can be omitted
#                 server.starttls(context=context)
#                 server.ehlo()  # Can be omitted
#                 server.login(sender_email, senderpassword)
#                 server.sendmail(sender_email, receiver_email, message)
#         # context = ssl.create_default_context()
#         # with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
#         #     server.login(sender_email, senderpassword)
#         #     server.sendmail(sender_email, receiver_email, message)
#             flash('An email has been sent with instructions to reset your password.', 'info')
#             return redirect(url_for('logion'))
#     return render_template('reset_request.html')


# @app.route("/reset_password/<token>", methods=['GET', 'POST'])
# def reset_token(token):
#     user = verify_reset_token(token)
#     if user is None:
#         flash('That is an invalid or expired token', 'warning')
#         return redirect(url_for('reset_request'))
#     form = ResetPasswordForm()
#     if form.validate_on_submit():
#         hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
#         user.password = hashed_password
#         flash(f'Your password has been updated! You are now able to log in', 'success')
#         return redirect(url_for('login'))
#     return render_template('reset_token.html', form=form)


# def send_reset_email(user):
#     print(user)
#     s = Serializer(app.config['SECRET_KEY'], 1800)
#     token  = s.dumps({'email': user}).decode('utf-8')
# #     msg = Message('Password Reset Request',
# #                   sender='immu@icorestack.io',
# #                   recipients=[user])
# #     msg.body = f'''To reset your password, visit the following link:
# # {url_for('reset_token', token=token, _external=True)}
# # If you did not make this request then simply ignore this email and no changes will be made.
# # '''
# #     mail.send(msg)


# def get_reset_token(self, expires_sec=1800):
#     s = Serializer(app.config['SECRET_KEY'], expires_sec)
#     return s.dumps({'email': self.email}).decode('utf-8')


@staticmethod
def verify_reset_token(token):
    s = Serializer(app.config['SECRET_KEY'])
    try:
        email = s.loads(token)['email']
    except:
        return None
    return email

# def send_reset_email(user):
#     s = Serializer(app.config['SECRET_KEY'], 1800)
#     token  = s.dumps({'email': user}).decode('utf-8')
#     msg = Message('Password Reset Request',
#                   sender='imran.hashmi226@gmail.com',
#                   recipients=[user])
#     msg.body = f'''To reset your password, visit the following link:
# {url_for('reset_token', token=token, _external=True)}
# If you did not make this request then simply ignore this email and no changes will be made.
# '''
#     mail.send(msg)


# @app.route("/reset_password", methods=['GET', 'POST'])
# def reset_request():
#     if request.method=='POST':
#         email= request.form['mail']
#         user = db.find_one({'email':email},{'_id':0,'email':1})
#         if user is not None:
#             s = Serializer(app.config['SECRET_KEY'], 1800)
#             token  = s.dumps({'email': user}).decode('utf-8')
#             msg = Message('Password Reset Request',
#                   sender='imran.hashmi226@gmail.com',
#                   recipients=[user])
#             msg.body = f'''To reset your password, visit the following link:
#             {url_for('reset_token', token=token, _external=True)}
# If you did not make this request then simply ignore this email and no changes will be made.
# '''
#             mail.send(msg)
#         flash('An email has been sent with instructions to reset your password.', 'info')
#         return redirect(url_for('home'))
#     return render_template('reset_request.html')








@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if request.method=='POST':
        email= request.form['mail']
        user = db.find_one({'email':email},{'_id':0,'email':1})
        if user is not None:
            s = Serializer(app.config['SECRET_KEY'], 1800)
            token  = s.dumps({'email': user['email']}).decode('utf-8')
            usere = user['email']
            msg = Message('Password Reset Request',
                  sender='imran.hashmi226@gmail.com',
                  recipients=[usere])
            msg.body = f'''To reset your password, visit the following link:
{url_for('reset_token', token=token, _external=True)}
If you did not make this request then simply ignore this email and no changes will be made.
'''
            mail.send(msg)
        # context = ssl.create_default_context()
        # with smtplib.SMTP_SSL(smtp_server, port, context=context) as server:
        #     server.login(sender_email, senderpassword)
        #     server.sendmail(sender_email, receiver_email, message)
            flash('An email has been sent with instructions to reset your password.', 'info')
            return redirect(url_for('logion'))
    return render_template('reset_request.html')




@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if session['email'] is not None:
        return redirect(url_for('home'))
    user = verify_reset_token(token)
    if user is None:
        flash('That is an invalid or expired token', 'warning')
        return redirect(url_for('reset_request'))
    if request.method=='POST':
        password = request.form["password"]
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
        db.update_one({'email':user},{'$set':{'password':hashed_password}})
        flash('Your password has been updated! You are now able to log in', 'success')
        return redirect(url_for('home'))
    return render_template('reset_token.html')




@app.route("/glogin")
def glogin():
    authorization_url, state = flow.authorization_url()
    session["state"] = state
    print("state",state)
    return redirect(authorization_url)


@app.route("/callback")
def callback():
    flow.fetch_token(authorization_response=request.url)

    if not session["state"] == request.args["state"]:
        abort(500)  # State does not match!

    credentials = flow.credentials
    request_session = requests.session()
    cached_session = cachecontrol.CacheControl(request_session)
    token_request = google.auth.transport.requests.Request(session=cached_session)

    id_info = id_token.verify_oauth2_token(
        id_token=credentials._id_token,
        request=token_request,
        audience=GOOGLE_CLIENT_ID
    )
    print(id_info)

    session["email"] = id_info.get("email")
    session['name'] = id_info.get('name')
    return redirect(url_for('home'))


@app.route("/generate_userposts",methods=['GET','POST'])
def generate_userposts():
    if request.method=='POST':
        words = request.form['words']
        generator = pipeline(task='text-generation', model='gpt2')
        blogs = generator(words, max_length=100, num_return_sequences=3)
        return render_template("post_generator.html",blogs=blogs)
    return render_template("post_generator.html")
    

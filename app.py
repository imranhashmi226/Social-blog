from flask import Flask,render_template,session
from flask_pymongo import PyMongo,ObjectId
from flask_bcrypt import Bcrypt
from flask_session import Session
from flask_mail import Mail


# from flask_login import LoginManager
import os
from flask import Flask, request, abort
app = Flask(__name__)
app.config['SECRET_KEY']= '5791628bb0b13ce0c676dfde280ba245'
app.config['MONGO_URI']="mongodb://localhost/sbs"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['MAIL_SERVER'] = 'smtp.googlemail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'imran.hashmi226@gmail.com'
app.config['MAIL_PASSWORD'] = 'wjeovbiumczcvnpf'
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"
mongo = PyMongo(app)

db = mongo.db.userinfo
postdb = mongo.db.postinfo
bcrypt = Bcrypt(app)
# login_manager = LoginManager()
# login_manager.init_app(app)
sessionv = Session(app)
mail = Mail(app)
# import declared routes
import routes

if __name__=="__main__":
    app.run(debug=True)
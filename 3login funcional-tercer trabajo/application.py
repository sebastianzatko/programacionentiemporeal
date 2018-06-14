from flask import Flask, g, render_template, jsonify, url_for, flash
from flask import request, redirect, make_response
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from functools import wraps
from database_setup import Base, User
import random
import string
import json
import datetime
import hashlib


app = Flask(__name__)
engine = create_engine('sqlite:///login.db?check_same_thread=false')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


@app.route('/register/', methods=['GET'])
def showRegister():
	return render_template('register.html')
	
def make_salt():
	return ''.join(random.choice(
				string.ascii_uppercase + string.digits) for x in range(32))
		
def make_pw_hash(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256((name + pw + salt).encode('utf-8')).hexdigest()
	return '%s,%s' % (salt, h)

def valid_pw(name, password, h):
	salt = h.split(',')[0]
	return h == make_pw_hash(name, password, salt)

@app.route('/', methods=['GET'])
@app.route('/public/', methods=['GET'])
def showMain():
	return render_template('index.html')

@app.route('/register/nuevousuario', methods=['POST'])
def nuevoUsuario():
	usuario=request.form['nombreusuario']
	contrasena=request.form['contrasena']
	email=request.form['email']
	
	pw_hash = make_pw_hash(usuario, contrasena)
	nuevoUsuario = User(
					username = usuario,
					email = email,
					pw_hash=pw_hash) 
	session.add(nuevoUsuario)
	session.commit()
	login_session['username'] = request.form['nombreusuario']
	return redirect(url_for('showMain'))
	
	
@app.route('/ingresar/',methods=['POST'])	
def login():
	user = session.query(User).filter_by(
			username = request.form['username']).first()

	if user and valid_pw(request.form['username'],
												request.form['password'],
												user.pw_hash):
	
		login_session['username'] = request.form['username']
		return render_template('main.html', username=login_session['username'])

	else:
		error = "Usuario no registrado!!!"
		return render_template('index.html', error = error)
	
	
	


if __name__ == '__main__':
	app.secret_key = "secret key"
	app.debug = True
	app.run(host = '0.0.0.0', port = 9000)

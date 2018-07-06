from flask import Flask, g, render_template, jsonify, url_for, flash
from flask import request, redirect, make_response
from flask import session as login_session
from sqlalchemy import create_engine
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from functools import wraps
from database_setup import Base, User,Pet,Publications,Comments,PetFriends
from oauth2client.client import flow_from_clientsecrets, FlowExchangeError
import random
import string
import json
import datetime
import hashlib
import httplib2
import requests
import os
from werkzeug.utils import secure_filename
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)

CLIENT_ID = json.loads(
		open('client_secrets.json', 'r').read())['web']['client_id']

engine = create_engine('sqlite:///login.db?check_same_thread=false')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


# GConnect
@app.route('/gconnect', methods=['POST'])
def gconnect():
	print ("Dentro de GConnect")
		# Validate state token
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid state parameter.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	# Obtain authorization code, now compatible with Python3
	code = request.data

	try:
			# Upgrade the authorization code into a credentials object
		oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
		oauth_flow.redirect_uri = 'postmessage'
		credentials = oauth_flow.step2_exchange(code)
	except FlowExchangeError:
		response = make_response(
					json.dumps('Failed to upgrade the authorization code.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response

	# Check that the access token is valid.
	access_token = credentials.access_token
	url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
				 % access_token)
	# Submit request, parse response - Python3 compatible
	h = httplib2.Http()
	result = json.loads(h.request(url, 'GET')[1])

	# If there was an error in the access token info, abort.
	if result.get('error') is not None:
			response = make_response(json.dumps(result.get('error')), 500)
			response.headers['Content-Type'] = 'application/json'
			return response

	# Verify that the access token is used for the intended user.
	gplus_id = credentials.id_token['sub']
	if result['user_id'] != gplus_id:
			response = make_response(
					json.dumps("Token's user ID doesn't match given user ID."), 401)
			response.headers['Content-Type'] = 'application/json'
			return response

	# Verify that the access token is valid for this app.
	if result['issued_to'] != CLIENT_ID:
			response = make_response(
					json.dumps("Token's client ID does not match app's."), 401)
			print ("Token's client ID does not match app's.")
			response.headers['Content-Type'] = 'application/json'
			return response

	stored_credentials = login_session.get('credentials')
	stored_gplus_id = login_session.get('gplus_id')
	if stored_credentials is not None and gplus_id == stored_gplus_id:
			response = make_response(json.dumps('Current user is already connected.'),
																	 200)
			response.headers['Content-Type'] = 'application/json'
			return response

	# Store the access token in the session for later use.
	login_session['access_token'] = credentials.access_token
	login_session['gplus_id'] = gplus_id

	# Get user info
	userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
	params = {'access_token': access_token, 'alt': 'json'}
	answer = requests.get(userinfo_url, params=params)

	data = answer.json()

	login_session['username'] = data['name']
	login_session['picture'] = data['picture']
	login_session['email'] = data['email']

	# user_id = getUserID(login_session['email'])
	# if not user_id:
	# 		user_id = createUser(login_session)

	# login_session['user_id'] = user_id

	output = ''
	output += '<h3>Welcome, '
	output += login_session['username']
	output += '!</h3>'
	output += '<img src="'
	output += login_session['picture']
	output += ' " style = "width: 100px; height: 100px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
	flash("you are now logged in as %s" % login_session['username'])
	print ("done!")
	print ("Usuario " + login_session['username'])
	return output
	

@app.route('/gdisconnect')
def gdisconnect():
				# Only disconnect a connected user.
		access_token = login_session.get('access_token')
		if access_token is None:
				response = make_response(
						json.dumps('Current user not connected.'), 401)
				response.headers['Content-Type'] = 'application/json'
				return response
		url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
		h = httplib2.Http()
		result = h.request(url, 'GET')[0]
		if result['status'] == '200':
				# Reset the user's sesson.
				del login_session['access_token']
				del login_session['gplus_id']
				del login_session['username']
				del login_session['email']
				del login_session['picture']
				response = make_response(json.dumps('Successfully disconnected.'), 200)
				response.headers['Content-Type'] = 'application/json'
				return redirect(url_for('showGenres'))
		else:
				# For whatever reason, the given token was invalid.
				response = make_response(
						json.dumps('Failed to revoke token for given user.', 400))
				response.headers['Content-Type'] = 'application/json'
		return response


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
	state = ''.join(random.choice(
			string.ascii_uppercase + string.digits) for x in range(32))
	# store it in session for later use
	login_session['state'] = state
	return render_template('index.html',STATE = state)

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
		login_session['id_user'] = user.id
		return redirect('/mypets/')

	else:
		error = "Usuario no registrado"
		return render_template('index.html', error = error)
	
@app.route('/home/<int:id>',methods=['GET','POST'])
def ShowHome(id):
	if login_session['id_user']:
		pet=session.query(Pet).filter_by(id = id).one()
		login_session['id_selectedpet']=id
		sql=text("SELECT id,petname,portrait FROM pet WHERE id NOT IN(select pet.id from pet inner join petfriends on petfriends.id_pet1=pet.id OR petfriends.id_pet2=pet.id WHere petfriends.id_pet1="+str(login_session['id_selectedpet'])+" or petfriends.id_pet1="+str(login_session['id_selectedpet'])+") AND pet.id!="+str(login_session['id_selectedpet'])+" ORDER BY RANDOM() LIMIT 5")
		result=session.execute(sql)
		
		return render_template('home.html', username=login_session['username'],pet=pet,suggestfriends=result)
	else:
		return redirect('/public/')
	
def allowed_file(filename):
	return '.' in filename and \
		filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/mypets/',methods=['GET'])
def petselect():
	if login_session['id_user']:
		pets=session.query(Pet).filter_by(id_user=login_session['id_user'])


		print("ENTRO Y YA DEBERIA HABER DADO LA QUERY:::::::::::::::"+str(login_session['id_user']))
		return render_template('petselect.html',username=login_session['username'],iduser=login_session['id_user'],pets=pets)
	else:
		return redirect('/public/')

@app.route('/createpet/',methods=['GET','POST'])
def CreatePet():
	if request.method=='GET':
		if login_session['id_user']:
			return render_template('createpet.html', username=login_session['username'])
		else:
			return redirect('/public/')
	if request.method=='POST':
		path=""
		nombre=request.form['petname']
		sexo=request.form['gender']
		animal=request.form['animal']
		file=request.files['files']
		iduser=login_session['id_user']
		if file is None:
			file=null
		else:
			if allowed_file(file.filename):
				filename = secure_filename(file.filename)
				stringid=str(iduser)
				path=os.path.join('static','subida', stringid)
				if os.path.isdir('static/subida/'+stringid+'/'):  # line A
					file.save(os.path.join('static','subida',stringid, filename))
				else:
					os.makedirs('static/subida/'+stringid+'/')       # line B
					file.save(os.path.join('static','subida',stringid, filename))
					
		pet = Pet(
				petname= nombre,
				sexo=sexo,
				datejoinedin = datetime.datetime.now(),
				animal=animal,
				portrait=path+"/"+filename,
				id_user=iduser) 
		session.add(pet)
		session.commit()
		return redirect(url_for('petselect'))
		

@app.route('/publicar/',methods=['POST'])
def publicar():
	content=request.form['content']
	
	if content:
		publicacion=Publications(
			content=content,
			date = datetime.datetime.now(),
			id_pet=login_session['id_selectedpet']
		)
		session.add(publicacion)
		session.commit()
		return jsonify({'content':content,'fecha':datetime.datetime.now()})
	
@app.route('/conseguirpublicaciones/',methods=['POST'])
def conseguirpublicaciones():
	
	consultasql=text("SELECT publications.id_publication,publications.content,publications.date,pet.petname,pet.portrait,pet.id FROM publications,pet WHERE publications.id_pet=pet.id ORDER BY datetime(publications.date) desc LIMIT "+request.form['start']+","+request.form['limit']+"")
	result=session.execute(consultasql)
	
	final=[]
	for x in result:
		var="<div class='row' id='separacionrwos'><div class='col-md-1 col-sm-1  col-lg-1 col-xs-1'></div><div class='col-md-10 col-sm-10  col-lg-10 col-xs-10'><div class='media'><div class='media-left'><img src='/"+x.portrait+"' class='img-circle thumnaillittle'/></div><div class='media-body'><a href='/seeprofile/"+str(x.id)+"'><h2>"+x.petname+"</h2></a><p>"+x.content+"</p></div><div class='media-right'><p>"+x.date+"</p></div></div><div class='col-md-1 col-sm-1  col-lg-1 col-xs-1'></div></div>"
		final.append(var);
	return jsonify({'content':final})

@app.route('/pet/delete/<int:id>',methods=['GET','POST'])
def eliminarmascota(id):
	pet=session.query(Pet).filter_by(id=id).one()
	if request.method=='GET':
		return render_template('delete-pet.html',pet=pet)
	if request.method=='POST':
		session.delete(pet)
		session.commit()
		return redirect('/mypets/')
	
@app.route('/pet/update/<int:id>',methods=['GET','POST'])
def updatemascota(id):
	if login_session['id_user']:
		pet=session.query(Pet).filter_by(id=id).one()
		if request.method=='GET':
			return render_template('update-pet.html',pet=pet)
		if request.method=='POST':
			pet.petname=request.form['petname']
			pet.sexo=request.form['gender']
			pet.animal=request.form['animal']
			session.add(pet)
			session.commit()
			return redirect('/mypets/')
	else:
		return redirect('/public/')
@app.route('/addfriend/',methods=['GET','POST'])	
def addfriend():
	id_peta=login_session['id_selectedpet']
	id_petb=request.form['friend']
	frienship=PetFriends(
		id_pet1=id_peta,
		id_pet2=id_petb,
		friendship=0
	)
	session.add(frienship)
	session.commit()
	
	sql=text("SELECT id,petname,portrait FROM pet WHERE id NOT IN(select pet.id from pet inner join petfriends on petfriends.id_pet1=pet.id OR petfriends.id_pet2=pet.id WHere petfriends.id_pet1="+str(login_session['id_selectedpet'])+" or petfriends.id_pet1="+str(login_session['id_selectedpet'])+") AND id!="+str(login_session['id_selectedpet'])+" ORDER BY RANDOM() LIMIT 1")
	result=session.execute(sql)
	for x in result:
		id=x.id
		portrait=x.portrait
		nombre=x.petname
	if id:
		return jsonify({'newstrangerid':id,'newstrangerportrait':portrait,'newstrangerpetname':nombre})
	else:
		return jsonify({'status':'OK'})

@app.route('/logoutpet/',methods=['GET'])
def logoutpet():
	del login_session['id_selectedpet']
	return redirect('/mypets/')

@app.route('/conseguirsuggest/',methods=['POST'])
def sugerir():
	sugerencia=request.form['suggest']
	
	id=login_session['id_selectedpet']
	sqlconfirmados=text("select pet.id,pet.portrait,pet.petname from pet where pet.id in (select pet.id from pet inner join petfriends on petfriends.id_pet1=pet.id OR petfriends.id_pet2=pet.id WHere (petfriends.id_pet1="+str(id)+" or petfriends.id_pet1="+str(id)+") AND petfriends.friendship=1) AND pet.id!="+str(id)+" AND pet.petname LIKE '%"+sugerencia+"%'")
	resultadoconfirmados=session.execute(sqlconfirmados)
	sql=text("SELECT id,petname,portrait FROM pet WHERE id NOT IN(select pet.id from pet inner join petfriends on petfriends.id_pet1=pet.id OR petfriends.id_pet2=pet.id WHere petfriends.id_pet1="+str(login_session['id_selectedpet'])+" or petfriends.id_pet1="+str(login_session['id_selectedpet'])+") AND pet.id!="+str(login_session['id_selectedpet'])+" AND pet.petname LIKE '%"+sugerencia+"%'")
	resultado=session.execute(sql)
	
	consultasql=text("SELECT publications.id_publication,publications.content,publications.date,pet.petname,pet.portrait,pet.id FROM publications,pet WHERE publications.id_pet=pet.id AND publications.content LIKE '%"+sugerencia+"%' ORDER BY datetime(publications.date) desc ")
	result=session.execute(consultasql)
	print(sqlconfirmados)
	print(sql)
	
		
	return render_template('busqueda.html',confirmados=resultadoconfirmados,sinagregar=resultado,publicaciones=result)


@app.route('/seeprofile/<int:id>',methods=['GET'])
def verperfil(id):
	if login_session['id_user']:
		visiterpet=login_session['id_selectedpet']
		pet=session.query(Pet).filter_by(id=id).one()
		sql=text("select publications.id_publication,publications.content,publications.date,pet.petname,pet.portrait FROM publications,pet where pet.id="+str(id)+" AND publications.id_pet="+str(id)+" ORDER BY datetime(publications.date) desc");
		resultpublicaciones=session.execute(sql)
		sqlamigos=text("select pet.id,pet.portrait,pet.petname from pet where pet.id in (select pet.id from pet inner join petfriends on petfriends.id_pet1=pet.id OR petfriends.id_pet2=pet.id WHere (petfriends.id_pet1="+str(id)+" or petfriends.id_pet1="+str(id)+") AND petfriends.friendship=1) AND pet.id!="+str(id)+"")
		resultfriends=session.execute(sqlamigos)
		return render_template('petprofile.html',pet=pet,idvisit=visiterpet,publicaciones=resultpublicaciones,amigos=resultfriends,idpet=id)
	else:
		return redirect('/public/')
	
@app.route('/eliminarpublicacion/',methods=['POST'])
def eliminarpublicacion():
	id=request.form['idpubli']
	print (id)
	publicacion=session.query(Publications).filter_by(id_publication=id).one()
	session.delete(publicacion)
	session.commit()
	return jsonify({'status':"OK"})

@app.route('/petfriends/',methods=['GET'])
def conseguiramigos():
	if login_session['id_user']:
		id=login_session['id_selectedpet']
		sqlpendientes=text("select pet.id,pet.portrait,pet.petname from pet where pet.id in (select pet.id from pet inner join petfriends on petfriends.id_pet1=pet.id OR petfriends.id_pet2=pet.id WHere (petfriends.id_pet1="+str(id)+" or petfriends.id_pet1="+str(id)+") AND petfriends.friendship=0) AND pet.id!="+str(id)+"")
		resultadopendientes=session.execute(sqlpendientes)
		sqlconfirmados=text("select pet.id,pet.portrait,pet.petname from pet where pet.id in (select pet.id from pet inner join petfriends on petfriends.id_pet1=pet.id OR petfriends.id_pet2=pet.id WHere (petfriends.id_pet1="+str(id)+" or petfriends.id_pet1="+str(id)+") AND petfriends.friendship=1) AND pet.id!="+str(id)+"")
		resultadoconfirmados=session.execute(sqlconfirmados)
		return render_template('pet-friends.html',pendientes=resultadopendientes,confirmados=resultadoconfirmados)
	else:
		return redirect('/public/')
@app.route('/confirmar/',methods=['POST'])
def confirmaramistad():
	id_pet1=login_session['id_selectedpet']
	id_pet2=request.form['idpet']
	sql=text("update petfriends set friendship=1 where (id_pet1="+str(id_pet1)+" AND id_pet2="+str(id_pet2)+") OR (id_pet1="+str(id_pet2)+" AND id_pet2="+str(id_pet1)+")")
	session.execute(sql)
	return jsonify({'status':"OK"})

@app.route('/agregaramigosinproblem/',methods=['POST'])
def agregaramigopiola():
	id_peta=login_session['id_selectedpet']
	id_petb=request.form['friend']
	frienship=PetFriends(
		id_pet1=id_peta,
		id_pet2=id_petb,
		friendship=0
	)
	session.add(frienship)
	session.commit()
	return jsonify({'status':'OK'})

@app.route('/cerrarsesion/',methods=['GET'])
def cerrarsesion():
	if login_session['id_user']:
		del login_session['username']
		del login_session['id_user']

	return redirect('/')
@app.route('/easyhome/',methods=['GET'])
def easyhome():
	if login_session['id_selectedpet']:
		return redirect('/home/'+str(login_session['id_selectedpet'])+'')
	else:
		return redirect('/public/')
		

if __name__ == '__main__':
	app.secret_key = "secret key"
	app.debug = True
	app.run(host = '0.0.0.0', port = 9000)

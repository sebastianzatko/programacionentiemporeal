import sys
import datetime
from sqlalchemy import Column, ForeignKey, Integer, String, DateTime,Boolean,Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine

Base = declarative_base()

class User(Base):
	__tablename__ = 'user'

	id = Column(Integer, primary_key=True)
	username = Column(String(50), nullable=False)
	email = Column(String(250), nullable=False)
	pw_hash = Column(String(250), nullable=False)
	imagen=Column(String(250), nullable=True)
	county=Column(String(100),nullable=True)
	city=Column(String(150),nullable=True)
	
	
class Pet(Base):
	__tablename__ = 'pet'

	id = Column(Integer, primary_key=True)
	petname= Column(String(50), nullable=False)
	animal = Column(String(100), nullable=False)
	portrait=Column(String(250),nullable=True)
	sexo=Column(String(15),nullable=True)
	datejoinedin=Column(DateTime,nullable=False)
	id_user=Column(Integer,ForeignKey("user.id"))
	user=relationship("User")
	
class Publications(Base):
	__tablename__ = 'publications'
	
	id_publication=Column(Integer,primary_key=True)
	content=Column(Text,nullable=False)
	date=Column(DateTime,nullable=False)
	
	id_pet=Column(Integer,ForeignKey("pet.id"))
	pet=relationship("Pet")
	
	
class Comments(Base):
	__tablename__ = 'comments'
	
	id_comment=Column(Integer,primary_key=True)
	content=Column(String(200),nullable=False)
	date=Column(DateTime,nullable=False)
	
	id_publication=Column(Integer,ForeignKey("publications.id_publication"))
	publication=relationship("Publications")
	
	id_pet=Column(Integer,ForeignKey("pet.id"))
	pet=relationship("Pet")
	
class PetFriends(Base):
	__tablename__ = 'petfriends'
	friendship=Column(Boolean,nullable=False)
	id = Column(Integer, primary_key=True)
	id_pet1=Column(Integer,ForeignKey("pet.id"))
	pet1=relationship("Pet",foreign_keys=[id_pet1])
	id_pet2=Column(Integer,ForeignKey("pet.id"))
	pet2=relationship("Pet",foreign_keys=[id_pet2])
	
	
	
	
	
	

engine = create_engine('sqlite:///login.db')
Base.metadata.create_all(engine)

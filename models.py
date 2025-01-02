from sqlalchemy.orm import relationship
from db import db
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
)
from datetime import datetime


class User(db.Model):
   __tablename__ = "users"

   id = Column(Integer, primary_key=True, autoincrement=True)
   created_at = Column(DateTime, default=datetime.utcnow)
   email = Column(String, nullable=False, unique=True)
   password = Column(String, nullable=False, unique=False)
   first_name = Column(String, nullable=False, unique=False)
   last_name = Column(String, nullable=False, unique=False)
   age = Column(Integer, nullable=False, unique=False)
   favorite_genre = Column(String, nullable=True, unique=False)
   
   messages = relationship("Message", back_populates="user")
   favorite_movies = relationship("FavoriteMovies", back_populates="user")
   favorite_genres = relationship("FavoriteGenres", back_populates="user")


class Message(db.Model):
   __tablename__ = "messages"
   id = Column(Integer, primary_key=True, autoincrement=True)
   created_at = Column(DateTime, default=datetime.utcnow)
   content = Column(Text, nullable=False)
   author = Column(String, nullable=False)
   user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
   
   user = relationship("User", back_populates="messages")
   
class FavoriteMovies(db.Model):
   __tablename__ = "favorite_movies"
   id = Column(Integer, primary_key=True, autoincrement=True)
   created_at = Column(DateTime, default=datetime.utcnow)
   name = Column(String, nullable=False, unique=False)
   user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
   
   user = relationship("User", back_populates="favorite_movies")

class FavoriteGenres(db.Model):
   __tablename__ = "favorite_genres"
   id = Column(Integer, primary_key=True, autoincrement=True)
   created_at = Column(DateTime, default=datetime.utcnow)
   name = Column(String, nullable=False, unique=False)
   user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
   
   user = relationship("User", back_populates="favorite_genres")
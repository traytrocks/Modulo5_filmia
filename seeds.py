from db import db
from app import app
from models import User, Message

with app.app_context():
    db.create_all()

    """ user = User(email="test@test.com",password="pass",first_name="First Name",last_name="Last Name",age=15)
    message = Message(content="Hola! Soy FilmIA, un recomendador de películas. ¿En qué te puedo ayudar?", author="assistant", user=user)

    db.session.add(user)
    db.session.add(message)
    db.session.commit() """
    
    print("Usuario y Mensaje creado!")
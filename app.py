from flask import Flask, flash, redirect, render_template, request
from flask_bootstrap import Bootstrap5
from openai import OpenAI
from dotenv import load_dotenv
from db import db, db_config
from models import User, Message, FavoriteMovies, FavoriteGenres
#from forms import ProfileForm, SignUpForm, LoginForm
from flask_wtf.csrf import CSRFProtect
from os import getenv
import json
from bot import search_movie_or_tv_show, search_movie_or_tvshows_trailer, search_movie_provider, search_trendings
from flask_login import LoginManager, login_required, login_user, current_user, logout_user
from flask_bcrypt import Bcrypt
from flask import redirect, url_for
from movies import search

load_dotenv()

login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.login_message = 'Inicia sesión para continuar'
client = OpenAI()
app = Flask(__name__)
app.secret_key = getenv('SECRET_KEY')
bootstrap = Bootstrap5(app)
#csrf = CSRFProtect(app)
login_manager.init_app(app)
bcrypt = Bcrypt(app)
db_config(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

tools = [
    {
        'type': 'function',
        'function': {
            "name": "search_movie_or_tv_show",
            "description": "Returns information about a specified movie or TV show.",
            "parameters": {
                "type": "object",
                "required": [
                    "name"
                ],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the movie/tv show to search for"
                    }
                },
                "additionalProperties": False
            }
        },
    },
    {
        'type': 'function',
        'function': {
            "name": "search_movie_or_tvshows_trailer",
            "description": "Returns a youtube url where to watch the trailer of a certain movie.",
            "parameters": {
                "type": "object",
                "required": [
                    "name"
                ],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the movie/tv show to search for"
                    }
                },
                "additionalProperties": False
            }
        },
    },
    {
        'type': 'function',
        'function': {
            "name": "search_movie_provider",
            "description": "Returns a list of providers where to watch a certain movie",
            "parameters": {
                "type": "object",
                "required": [
                    "name"
                ],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "The name of the movie/tv show to search for"
                    }
                },
                "additionalProperties": False
            }
        },
    },
    {
        'type': 'function',
        'function': {
            "name": "search_trendings",
            "description": "Return a movie that is in trending",
        },
    },
]

@app.route('/')
def home():
    return render_template('landing.html')   

@app.route('/signup', methods=['GET', 'POST'])
def signUp():

    error_msg = ""
    success_msg = ""
    msg = ""
    
    if request.method == 'GET':
        return render_template('signUp.html', error_msg=error_msg)
    
    email = request.form.get('email')
    password = request.form.get('password')
    fname = request.form.get('fname')
    lname = request.form.get('lname')
    age = request.form.get('age')
    
    exists = db.session.query(db.exists().where(User.email == email)).scalar()
    
    if exists:
        error_msg = "Este correo ya fue usado por otro usuario."
    else:
        user = User(email=email, password=password, first_name=fname,last_name=lname,age=age)
        db.session.add(user)
        db.session.add(Message(content="Hola! Soy FilmIA, un recomendador de películas. ¿En qué te puedo ayudar?", author="assistant", user=user))
        db.session.commit()
        success_msg = "Cuenta creada con exito."
        msg = "Volver a inicio"
        
    return render_template('signUp.html', error_msg=error_msg, success_msg=success_msg, msg=msg)

@app.route('/signin', methods=['GET', 'POST'])
def signIn():
    
    error_msg = ""
    
    if request.method == 'GET':
        return render_template('signIn.html')
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = db.session.execute(db.select(User).filter_by(email=email)).scalar()
    
    if user is None:
        error_msg = "El usuario no existe."
    else:
        if user.password != password:
            error_msg = "Contraseña incorrecta."
        else:
            return redirect(f'/user/{user.id}/chat')
        
    return render_template('signIn.html', error_msg=error_msg)
        

@app.route('/user/<id>/chat', methods=['GET', 'POST'])
def chat(id):
    user = db.session.execute(db.select(User).filter_by(id=int(id))).scalar_one()
    fav_movies = ', '.join([movie.name for movie in user.favorite_movies])
    fav_genres = ', '.join([genre.name for genre in user.favorite_genres])
    profile_url = "/user/"+str(id)+"/profile"
    movie_params = {}

    if request.method == 'GET':
        return render_template('chat.html', user=user, profile_url=profile_url, movie_params=movie_params)

    if request.method == 'POST':

        intent = request.form.get('intent')

        intents = {
            'Genero favorito': f'Recomiéndame una película basada en mis generos favoritos que son : {fav_genres}',
            'Peliculas favoritas': f'Recomiéndame una película basada en mis peliculas favoritas que son : {fav_movies}',
            'Quiero algo distinto': f'Recomiéndame una película alejada de mis gustos favoritos, que no sean {fav_genres} y que no se parezcan a {fav_movies}',
            'Tendencia': 'Recomiéndame algo en tendencia',
            'Enviar': request.form.get('message')
        }

        if intent in intents:
            user_message = intents[intent]

            db.session.add(Message(content=user_message, author="user", user=user))
            db.session.commit()

            messages_for_llm = [{
                "role": "system",
                "content": "Eres un chatbot que recomienda películas, te llamas 'Filmia'. Tu rol es responder recomendaciones de manera breve y concisa. No repitas recomendaciones, usa prioritariamente cualquier enlace que venga desde la api tmdbsimple",
            }]

            for message in user.messages:
                messages_for_llm.append({
                    "role": message.author,
                    "content": message.content,
                })

            chat_completion = client.chat.completions.create(
                messages=messages_for_llm,
                model="gpt-4o",
                temperature=1,
                tools=tools
            )
            
            if chat_completion.choices[0].message.tool_calls:
                tool_call = chat_completion.choices[0].message.tool_calls[0]
                if tool_call.function.name == 'search_trendings':
                    arguments = json.loads(tool_call.function.arguments)
                    model_recommendation = search_trendings(client, user_message)
                elif tool_call.function.name == 'search_movie_or_tv_show':
                    arguments = json.loads(tool_call.function.arguments)
                    name = arguments['name']
                    model_recommendation = search_movie_or_tv_show(client, name, user_message)
                elif tool_call.function.name == 'search_movie_or_tvshows_trailer':
                    arguments = json.loads(tool_call.function.arguments)
                    name = arguments['name']
                    model_recommendation = search_movie_or_tvshows_trailer(client, name, user_message)
                elif tool_call.function.name == 'search_movie_provider':
                    arguments = json.loads(tool_call.function.arguments)
                    name = arguments['name']
                    model_recommendation = search_movie_provider(client, name, user_message)
            else:
                model_recommendation = chat_completion.choices[0].message.content

            if model_recommendation.find('"') != -1:
                movie = model_recommendation.split('"')[1]
                result = search(movie)
                movie_params['original_title'] = result['original_title']
                movie_params['overview'] = result['overview']
                movie_params['poster_path'] = 'https://image.tmdb.org/t/p/original'+result['poster_path']
                movie_params['release_date'] = result['release_date']
                movie_params['vote_average'] = result['vote_average']
            
            db.session.add(Message(content=model_recommendation, author="assistant", user=user))
            db.session.commit()

        return render_template('chat.html', user=user, profile_url=profile_url, movie_params=movie_params)
    
@app.route('/user/<id>/profile', methods=['GET', 'POST'])
def user(id):
    user = db.get_or_404(User, id)
    chat_url = "/user/"+str(id)+"/chat"
    editable = False
    
    if request.method == 'POST':
        if request.form["profile_info"] == "Cancelar":
            editable = False
        if request.form["profile_info"] == "Editar":
            editable = True
        if request.form["profile_info"] == "Guardar":
            editable = False
            fname = request.form.get('fname')
            lname = request.form.get('lname')
            age = request.form.get('age')
            user = db.session.execute(db.select(User).filter_by(id=int(id))).scalar_one()
            user.first_name = fname
            user.last_name = lname
            user.age = age
            db.session.commit()
        if request.form["profile_info"] == "Agregar":
            movie = request.form.get('movie')
            genre = request.form.get('genre')
            if movie:
                db.session.add(FavoriteMovies(name=movie, user_id=int(id)))
            if genre:
                db.session.add(FavoriteGenres(name=genre, user_id=int(id)))
            db.session.commit()
        if request.form["profile_info"] == "Eliminar":
            movie_id = request.form.get('movie_id')
            genre_id = request.form.get('genre_id')
            if movie_id:
                movie_to_delete = db.session.query(FavoriteMovies).filter_by(id=movie_id).scalar()
                db.session.delete(movie_to_delete)
            if genre_id:
                genre_to_delete = db.session.query(FavoriteGenres).filter_by(id=genre_id).scalar()
                db.session.delete(genre_to_delete)
            db.session.commit()
    return render_template('user.html', user=user, editable=editable, chat_url=chat_url)
from flask import Flask, flash, redirect, render_template, request, session, jsonify
from flask_bootstrap import Bootstrap5
from openai import OpenAI
from dotenv import load_dotenv
from db import db, db_config
from flask_migrate import Migrate
from models import User, Message, FavoriteMovies, FavoriteGenres
from os import getenv
import json
from bot import search_movie_or_tv_show, search_movie_or_tvshows_trailer, search_movie_provider, search_trendings
from flask_login import LoginManager, login_required, logout_user, login_user, current_user
from flask import redirect, url_for
from movies import search
from flask_bcrypt import Bcrypt



load_dotenv()

login_manager = LoginManager()
login_manager.session_protection = "strong"
login_manager.login_view = 'signin'
login_manager.login_message_category = "info"
login_manager.login_message = 'Inicia sesión para continuar'

client = OpenAI()
app = Flask(__name__)
app.secret_key = getenv('SECRET_KEY')
bootstrap = Bootstrap5(app)
db_config(app)
bcrypt = Bcrypt(app)
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    #print(f"load_user: {user_id}", flush=True)
    user = db.session.query(User).get(int(user_id))
    return user if user else None


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
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    return render_template('landing.html')

@app.route('/signup', methods=['GET', 'POST'])
def signUp():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
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
    
    if db.session.query(User).filter_by(email=email).first():
        error_msg = "Hubo un problema al registrar el usuario."
    else:
        user = User(email=email, 
                    password=bcrypt.generate_password_hash(password).decode('utf-8'), 
                    first_name=fname, 
                    last_name=lname, 
                    age=age)
        db.session.add(user)
        db.session.add(Message(content="Hola! Soy FilmIA, un recomendador de películas. ¿En qué te puedo ayudar?", author="assistant", user=user))
        db.session.commit()
        success_msg = "Cuenta creada con éxito."
        msg = "Volver a inicio"
        
    return render_template('signUp.html', error_msg=error_msg, success_msg=success_msg, msg=msg)

@app.route('/signin', methods=['GET', 'POST'])
def signIn():
    if current_user.is_authenticated:
        return redirect(url_for('chat'))
    if request.method == 'GET':
        return render_template('signIn.html')
    
    email = request.form.get('email')
    password = request.form.get('password')
    
    user = db.session.query(User).filter_by(email=email).first()
    
    if user is None:
        return render_template('signIn.html', error_msg="Hubo un problema al iniciar sesión.")

    if not bcrypt.check_password_hash(user.password, password):
        return render_template('signIn.html', error_msg="Correo o contraseña incorrectos.")

    session['email'] = email
    login_user(user)
    return redirect(url_for('chat'))

@app.route('/chat', methods=['GET', 'POST'])
@login_required
def chat():
    email = session.get('email')
    user = db.session.query(User).filter_by(email=email).first()
    fav_movies = ', '.join([movie.name for movie in user.favorite_movies])
    fav_genres = ', '.join([genre.name for genre in user.favorite_genres])
    profile_url = "/profile"
    movie_params = {}

    if request.method == 'GET':
        print("Entra al get de chat", flush=True)
        return render_template('chat.html', user=user, profile_url=profile_url, movie_params=movie_params)

    intent = request.form.get('intent')
    
    user_message = str(request.json.get('message', ''))
    
    intents = {
        'Genero favorito': f'Recomiéndame una película basada en mis géneros favoritos que son : {fav_genres}',
        'Películas favoritas': f'Recomiéndame una película basada en mis películas favoritas que son : {fav_movies}',
        'Quiero algo distinto': f'Recomiéndame una película alejada de mis gustos favoritos, que no sean {fav_genres} y que no se parezcan a {fav_movies}',
        'Tendencia': 'Recomiéndame algo en tendencia',
        'Enviar': user_message,
    }
    #print(intent, flush=True)
    if user_message not in intents:
        intent = 'Enviar'
    else:
        intent = user_message
    

    user_message = intents[intent]

    db.session.add(Message(content=user_message, author="user", user=user))
    db.session.commit()

    messages_for_llm = [{
        "role": "system",
        "content": "Eres un chatbot que recomienda películas, te llamas 'FilmIA'. Tu rol es responder recomendaciones de manera breve y concisa. No repitas recomendaciones, usa prioritariamente cualquier enlace que venga desde la api tmdbsimple",
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
        #print(f"result: {result}", flush=True)
        movie_params['original_title'] = result.get('original_title')
        movie_params['overview'] = result.get('overview')
        movie_params['poster_path'] = 'https://image.tmdb.org/t/p/original'+result['poster_path']
        movie_params['release_date'] = result.get('release_date')
        movie_params['vote_average'] = result.get('vote_average')
    
    
    chatbot_response = Message(content=model_recommendation, author="assistant", user=user)
    db.session.add(chatbot_response)
    db.session.commit()
    
    accept_header = request.headers.get('Accept')
    if accept_header and 'application/json' in accept_header:
        return {
            "message": {
                "author": chatbot_response.author,
                "content": chatbot_response.content,
            },
            "movie_params": movie_params
        }, 200
                
    print("llega al final", flush=True)
    return render_template('chat.html', user=user, profile_url=profile_url, movie_params=movie_params)

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def user():
    user = db.session.query(User).filter_by(email=current_user.email).first()
    chat_url = "/chat"
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
            user.first_name = fname
            user.last_name = lname
            user.age = age
            
            db.session.commit()
        if request.form["profile_info"] == "Agregar":
            movie = request.form.get('movie')
            genre = request.form.get('genre')
            if movie:
                db.session.add(FavoriteMovies(name=movie, user=user))
            if genre:
                db.session.add(FavoriteGenres(name=genre, user=user))
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


@app.route('/logout')
def logout():
    logout_user()
    session.pop('email', None)
    return redirect(url_for('home'))

@login_manager.unauthorized_handler
def unauthorized_handler():
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
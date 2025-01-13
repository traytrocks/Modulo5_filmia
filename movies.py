import tmdbsimple as tmdb
from dotenv import load_dotenv
from os import getenv

load_dotenv()
tmdb.API_KEY = getenv('TMDB_API_KEY')


def search(movie_name):
    search = tmdb.Search()
    response = search.multi(query=movie_name, language='es-CL')

    if not search.results:
        return None

    return search.results[0]

def search_provider(movie_name):
    movie = search(movie_name)
    movie_id = movie['id']
    
    movie = tmdb.Movies(movie_id)
    provider_response = movie.watch_providers()
    
    if 'CL' in provider_response['results']:
        return provider_response['results']['CL']
    return 'No es posible ver la pelicula en Chile.'

def get_youtube_trailer(movie_name):
    movie = search(movie_name)
    movie_id = movie['id']

    movie = tmdb.Movies(movie_id)
    trailer_response = movie.videos()
    
    if trailer_response['results']:
        for trailer in trailer_response['results']:
            if trailer['type'] == 'Trailer':
                return trailer
    return 'No se encontraron trailer en la plataforma YouTube'

def get_trending():
    trends = ''
    trending = tmdb.Trending('movie','week')
    trending_response = trending.info()
        
    if trending_response:
        for trend in trending_response['results']:
            trends = trends + trend['title'] + ', '
        return trends
    return 'No se encontraron tendencias'
from movies import search, get_youtube_trailer, search_provider, get_trending
from openai import OpenAI
from models import User


def build_prompt():
    system_prompt = '''Eres un chatbot que recomienda películas, te llamas 'FilmIA'.
    - Tu rol es responder recomendaciones de manera breve y concisa.
    - No repitas recomendaciones.
    - Recuerda siempre mencionar la pelicula
    '''

    #if context:
    #    system_prompt += f'Además al final de tu respuesta escribeme siempre este mensaje, necesito validar la informacion: {context}\n'

    return system_prompt

def search_movie_or_tv_show(client: OpenAI, search_term: str, user_message: str):
    movie_or_tv_show = search(search_term)

    system_prompt = build_prompt()

    messages_for_llm = [{"role": "system", "content": system_prompt}]

    messages_for_llm.append({
        "role": "user",
        "content": user_message,
    })

    chat_completion = client.chat.completions.create(
        messages=messages_for_llm,
        model="gpt-4o",
        temperature=1,
    )

    return chat_completion.choices[0].message.content

def search_movie_or_tvshows_trailer(client: OpenAI, search_term: str, user_message: str):
    trailer = get_youtube_trailer(search_term)
    
    
    system_prompt = build_prompt() + f'Ademas, te entrego el json que tiene la key del trailer de youtube: {trailer}.'

    messages_for_llm = [{"role": "system", "content": system_prompt}]

    messages_for_llm.append({
        "role": "user",
        "content": user_message,
    })

    chat_completion = client.chat.completions.create(
        messages=messages_for_llm,
        model="gpt-4o",
        temperature=1,
    )

    return chat_completion.choices[0].message.content

def search_movie_provider(client: OpenAI, search_term: str, user_message: str):
    provider = search_provider(search_term)

    system_prompt = build_prompt() + f'Ademas, te entrego esta informacion oficial para que la uses: {provider}.'


    messages_for_llm = [{"role": "system", "content": system_prompt}]

    messages_for_llm.append({
        "role": "user",
        "content": user_message,
    })

    chat_completion = client.chat.completions.create(
        messages=messages_for_llm,
        model="gpt-4o",
        temperature=1,
    )

    return chat_completion.choices[0].message.content

def search_trendings(client: OpenAI, user_message: str):
    trending = get_trending()

    system_prompt = build_prompt() + f'Ademas, te entrego esta lista de peliculas en tendencia, elige una: {trending}.'


    messages_for_llm = [{"role": "system", "content": system_prompt}]

    messages_for_llm.append({
        "role": "user",
        "content": user_message,
    })

    chat_completion = client.chat.completions.create(
        messages=messages_for_llm,
        model="gpt-4o",
        temperature=1,
    )

    return chat_completion.choices[0].message.content
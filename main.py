import json, os
from fastapi import FastAPI
from starlette.requests import Request
from bs4 import BeautifulSoup
import requests, json, os
from openai import OpenAI
from dotenv import load_dotenv
from prompts import PROMPT_ALL_MOVIES, PROMPT_RATED_MOVIES
from models import Movies, MovieRecommendations, SessionLocal, Users, RatedMovies

app = FastAPI()
load_dotenv()

@app.get("/check_acc/{lb_username}")
async def check_acc(lb_username: str):
    if os.path.exists('profiles/' + lb_username + '.json'):
        with open('profiles/' + lb_username + '.json', 'r') as file:
            existing_recc = json.loads(file.read())
            return {"status": True, "recommendations": existing_recc['recommendations']}
    else:
        return {"status": False}


@app.get("/add_lb/{lb_username}")
async def add_lb(lb_username: str):
    URL = "https://letterboxd.com/" + lb_username + "/films/"
    
    page = requests.get(URL)

    soup = BeautifulSoup(page.content, "html.parser")

    pages = soup.find_all('li', class_='paginate-page')
    results = soup.find_all('li', class_='poster-container')
    with SessionLocal() as db:
        if len(pages) > 1:
            current_page = 2
            while current_page <= len(pages):
                next_page = URL + "page/" + str(current_page) + "/"
                next_page_html = requests.get(next_page)
                new_page_soup = BeautifulSoup(next_page_html.content, "html.parser")
                results += new_page_soup.find_all('li', class_='poster-container')
                current_page += 1
                
        all_movies = []
        all_movie_titles = []
        rated_movies = []

        for movie in results:
            movie_title = movie.find("div", class_='film-poster').find('img')['alt']
            movie_id = movie.find("div", class_='film-poster')['data-film-id']
            rating = movie.find("p", class_='poster-viewingdata').find('span', class_='rating')
            all_movies.append({
                "title": movie_title,
                "id" : movie_id,
            })
            db.add(Movies(
                title = movie_title
            ))
            db.commit()
            all_movie_titles.append(movie_title)
            if rating is not None:
                for key in rating.attrs['class']:
                    if 'rated-' in key:
                        rated_movies.append({
                            "title": movie_title,
                            "id" : movie_id,
                            "rating" : key.split("-")[1] + "/10"
                        })
                        db.add(RatedMovies(
                            title = movie_title,
                            imdb_id = int(movie_id),
                            rating = int(key.split("-")[1])
                        ))
                        db.commit()

        return {
            "all_movies": all_movie_titles,
            "rated_movies": rated_movies
        }

@app.post("/generate/{lb_username}")
async def generate(request : Request, lb_username : str):
    with SessionLocal() as db:
        user_id = db.query(Users).filter(Users.lb_username == lb_username).first()
        if not user_id:
            new_user = Users(
                lb_username = lb_username
            )
            db.add(new_user)
            db.commit()

    body = await request.json()
    analysis_type = body['type']
    all_movies = body['all_movies']
    rated_movies = body['rated']

    client = OpenAI(api_key=os.getenv('OPENAI_KEY'))

    movie_prompt = { "input_movies" : rated_movies if analysis_type == 'rated' else all_movies}

    completion = client.beta.chat.completions.parse(
    model="gpt-4o-2024-08-06",
    messages=[
        {"role": "system", "content": PROMPT_RATED_MOVIES if analysis_type == 'rated' else PROMPT_ALL_MOVIES},
        {"role": "user", "content": json.dumps(movie_prompt)}
    ],
    response_format=MovieRecommendations
    )

    recommended_movies = []
    recommendations = completion.choices[0].message.parsed
    for movie in recommendations.recommended_movies:
        print(movie.title)
        recommended_movies.append(movie.title)

    return {
        "type" : analysis_type,
        "count_all" : len(all_movies),
        "count_rated" : len(rated_movies),
        "recommeds" : recommended_movies
    }

@app.post("/enrich/{lb_username}")
async def enrich(request : Request, lb_username : str):

    body = await request.json()
    recommendations = body['recommendations']
    for movie in recommendations:
        try:
            omdb_url = f"http://www.omdbapi.com/?apikey={os.getenv('OMDB_KEY')}&t={movie}"
            r = requests.get(omdb_url)
            data = r.json()
            with SessionLocal() as db:
                add_movie_from_json(db, data)
        except:
            print(data)
            print(movie)


    return {"status" : "done"}


def add_movie_from_json(session: SessionLocal, movie_data: dict):

    mapped_data = {
        'title': movie_data.get('Title'),
        'year': movie_data.get('Year'),
        'rated': movie_data.get('Rated'),
        'released': movie_data.get('Released'),
        'runtime': movie_data.get('Runtime'),
        'genre': movie_data.get('Genre'),
        'director': movie_data.get('Director'),
        'writer': movie_data.get('Writer'),
        'actors': movie_data.get('Actors'),
        'plot': movie_data.get('Plot'),
        'language': movie_data.get('Language'),
        'country': movie_data.get('Country'),
        'awards': movie_data.get('Awards'),
        'poster': movie_data.get('Poster'),
        'metascore': movie_data.get('Metascore'),
        'imdb_rating': movie_data.get('imdbRating'),
        'imdb_votes': movie_data.get('imdbVotes'),
        'imdb_id': movie_data.get('imdbID'),
        'type': movie_data.get('Type'),
        'dvd': movie_data.get('DVD'),
        'box_office': movie_data.get('BoxOffice'),
        'production': movie_data.get('Production'),
        'website': movie_data.get('Website'),
        'response': movie_data.get('Response')
    }

    
    new_movie = Movies(**mapped_data)

    session.add(new_movie)
    session.commit()

    return new_movie
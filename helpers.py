

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests, json, os, urllib.parse
from models import Movies, Recommendations, WatchedMovies, MovieRecommendations, Users, SessionLocal
from openai import OpenAI
from prompts import PROMPT_ALL_MOVIES, PROMPT_RATED_MOVIES

load_dotenv()

def check_lb_user_exists(lb_username):
    
    URL = "https://letterboxd.com/" + lb_username + "/films/"
    page = requests.get(URL)
    return True if page.status_code == 200 else False


def scrape_user_movies(lb_username, user):
    with SessionLocal() as db:
        user.status = 'scraping'
        db.commit()
        URL = "https://letterboxd.com/" + lb_username + "/films/"
        
        page = requests.get(URL)

        soup = BeautifulSoup(page.content, "html.parser")

        pages = soup.find_all('li', class_='paginate-page')
        results = soup.find_all('li', class_='poster-container')
        if len(pages) > 1:
            current_page = 2
            while current_page <= len(pages):
                next_page = URL + "page/" + str(current_page) + "/"
                next_page_html = requests.get(next_page)
                new_page_soup = BeautifulSoup(next_page_html.content, "html.parser")
                results += new_page_soup.find_all('li', class_='poster-container')
                current_page += 1
                
        all_movie_titles = []
        rated_movies = []

        for movie in results:
            movie_title = movie.find("div", class_='film-poster').find('img')['alt']
            lb_movie_id = movie.find("div", class_='film-poster')['data-film-id']
            is_rated = False
            rating = movie.find("p", class_='poster-viewingdata').find('span', class_='rating')
            if rating is not None:
                for key in rating.attrs['class']:
                    if 'rated-' in key:
                        is_rated = True
                        rating = int(key.split("-")[1]) 
                        

            all_movie_titles.append(
                { 
                    "title" : movie_title,
                    "lb_movie_id" : lb_movie_id,
                    "rated" : is_rated,
                    "rating" : rating if is_rated else None
                }
            )

        user.status = 'movie_data'
        db.commit()

        for movie in all_movie_titles:
            is_saved = db.query(Movies).filter(Movies.lb_movie_id == movie['lb_movie_id']).first()
            if not is_saved:
                new_movie_data = enrich_movie_data(movie['title'])
                new_movie = add_movie_from_json(db, new_movie_data, movie['lb_movie_id'])
            
            watched_movie = WatchedMovies(
                movie_id = new_movie.id if not is_saved else is_saved.id,
                user_id = int(db.query(Users.id).filter(Users.lb_username == lb_username).first()[0]),
                rating = movie['rating'] if movie['rated'] else 0
            )
            db.add(watched_movie)
            db.commit()
        
         

def enrich_movie_data(movie):
        omdb_url = f"http://www.omdbapi.com/?apikey={os.getenv('OMDB_KEY')}&t={urllib.parse.quote_plus(movie)}"
        r = requests.get(omdb_url)
        data = r.json()
        return data


def add_movie_from_json(session, movie_data, lb_movie_id):

    is_existing = session.query(Movies).filter(Movies.imdb_id == movie_data.get('imdbID')).first()
    if is_existing:
        is_existing.lb_movie_id = lb_movie_id
        session.commit()
        return is_existing

    mapped_data = {
        'title': movie_data.get('Title'),
        'lb_movie_id': lb_movie_id,
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
    }

    
    new_movie = Movies(**mapped_data)

    session.add(new_movie)
    session.commit()

    return new_movie

def generate_movie_ideas(lb_username, type):

    with SessionLocal() as db:
        user = db.query(Users).filter(Users.lb_username == lb_username).first()
        
        input_movies = []

        if type == 'rated':
            watched_movies_ids = db.query(WatchedMovies.movie_id, WatchedMovies.rating).filter(WatchedMovies.user_id == user.id, WatchedMovies.rating > 0).all()
            for movie_id, rating in watched_movies_ids:
                input_movies.append({
                    "title" : db.query(Movies.title).filter(Movies.id == movie_id).first()[0],
                    "rating" : rating
                })

        else:
            watched_movies_ids = db.query(WatchedMovies.movie_id).filter(WatchedMovies.user_id == user.id).all()
            watched_movies_ids = [movie_id for (movie_id,) in watched_movies_ids]
            input_movies = db.query(Movies.title).filter(Movies.id.in_(watched_movies_ids)).all()
            input_movies = [title for (title,) in input_movies]

        client = OpenAI(api_key=os.getenv('OPENAI_KEY'))

        movie_prompt = { "input_movies" : input_movies }

        completion = client.beta.chat.completions.parse(
        model="gpt-4o-2024-08-06",
        messages=[
            {"role": "system", "content": PROMPT_RATED_MOVIES if type == 'rated' else PROMPT_ALL_MOVIES},
            {"role": "user", "content": json.dumps(movie_prompt)}
        ],
        response_format=MovieRecommendations
        )

        recommended_movies = []
        recommendations = completion.choices[0].message.parsed
        for movie in recommendations.recommended_movies:
            print(movie.title)
            recommended_movies.append(movie.title)
            data = enrich_movie_data(movie.title)
            db_movie = db.query(Movies).filter(Movies.imdb_id == data.get('imdbID')).first()
            if not db_movie:
                db_movie = add_movie_from_json(db, data, None)

            recc = Recommendations(
                user_id = user.id,
                movie_id = db_movie.id
            )
            db.add(recc)
            db.commit()

        return recommended_movies
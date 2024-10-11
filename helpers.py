

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import requests, json, os



from models import Movies, RatedMovies, Users, SessionLocal

load_dotenv()



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
                    "rated" : is_rated,
                    "rating" : rating if is_rated else None
                }
            )
        
        for movie in all_movie_titles:
            new_movie = enrich_movie_data(movie['title'], db, user.id )
            if movie['rated']:
                rated_movie = RatedMovies(
                    movie_id = new_movie,
                    user_id = int(db.query(Users.id).filter(Users.lb_username == lb_username).first()[0]),
                    rating = movie['rating']
                )
                db.add(rated_movie)
                db.commit()
        
         

def enrich_movie_data(movie, db, user_id):
        omdb_url = f"http://www.omdbapi.com/?apikey={os.getenv('OMDB_KEY')}&t={movie}"
        r = requests.get(omdb_url)
        data = r.json()
        new_movie = add_movie_from_json(db, data, user_id)
        return new_movie.id


def add_movie_from_json(session, movie_data, user_id):

    mapped_data = {
        'title': movie_data.get('Title'),
        'user_id': user_id,
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
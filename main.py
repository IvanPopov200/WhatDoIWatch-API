import json, os
from fastapi import FastAPI
from typing import List
from starlette.requests import Request
from bs4 import BeautifulSoup
import requests, json, os
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel
from prompts import PROMPT_ALL_MOVIES, PROMPT_RATED_MOVIES
from pydantic import BaseModel
from typing import List
from fastapi import FastAPI

class RecommendedMovie(BaseModel):
    title: str

class MovieRecommendations(BaseModel):
    input_movies: List[str]
    recommended_movies: List[RecommendedMovie]


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
        all_movie_titles.append(movie_title)
        if rating is not None:
            for key in rating.attrs['class']:
                if 'rated-' in key:
                    rated_movies.append({
                        "title": movie_title,
                        "id" : movie_id,
                        "rating" : key.split("-")[1] + "/10"
                    })

    return {
        "all_movies": all_movie_titles,
        "rated_movies": rated_movies
    }

@app.post("/generate/{lb_username}")
async def generate(request : Request, lb_username : str):
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
    enriched_data = []
    for movie in recommendations:
        omdb_url = f"http://www.omdbapi.com/?apikey={os.getenv('OMDB_KEY')}&t={movie}"
        r = requests.get(omdb_url)
        data = r.json()
        enriched_data.append(data)

    print(data)
    with open(f'profiles/{lb_username}.json', 'w') as file:
        file.write(json.dumps(enriched_data))
    return enriched_data

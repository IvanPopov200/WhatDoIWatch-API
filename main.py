from multiprocessing import Process
import json, os
from fastapi import FastAPI, BackgroundTasks
from helpers import scrape_user_movies
from starlette.requests import Request
import json, os
from openai import OpenAI
from dotenv import load_dotenv
from prompts import PROMPT_ALL_MOVIES, PROMPT_RATED_MOVIES
from models import Movies, MovieRecommendations, SessionLocal, Users

app = FastAPI()
load_dotenv()

@app.get("/check_user/{lb_username}")
async def check_acc(lb_username: str, background_tasks: BackgroundTasks):
    with SessionLocal() as db:
        user = db.query(Users).filter(Users.lb_username == lb_username).first()
        if not user:
            new_user = Users(
                lb_username = lb_username, 
                status = 'new_user'
            )
            db.add(new_user)
            db.commit()

            background_tasks.add_task(scrape_user_movies, lb_username, new_user)

            return {"status" : new_user.status}

        else:
            user_movies = db.query(Movies).filter(Movies.user_id == user.id).all()


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




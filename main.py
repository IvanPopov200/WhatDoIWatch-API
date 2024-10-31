from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from helpers import check_lb_user_exists, generate_movie_ideas, scrape_user_movies
from dotenv import load_dotenv
from models import Movies, Recommendations, SessionLocal, Users, WatchedMovies

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
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
            return {"status" : user.status}


@app.get("/generate/{lb_username}/{analysis_type}")
async def generate(lb_username : str, analysis_type : str, background_tasks: BackgroundTasks):

    background_tasks.add_task(generate_movie_ideas, lb_username, analysis_type)

    return {"status" : "analysis_started"}



@app.get("/status/{lb_username}")
async def status(lb_username: str):
    with SessionLocal() as db:

        user = db.query(Users).filter(Users.lb_username == lb_username).first()
        if user:
            results = (
            db.query(
                Movies.id,
                Movies.title,
                Movies.lb_movie_id,
                Movies.year,
                Movies.rated,
                Movies.released,
                Movies.runtime,
                Movies.genre,
                Movies.director,
                Movies.writer,
                Movies.actors,
                Movies.plot,
                Movies.language,
                Movies.country,
                Movies.awards,
                Movies.poster,
                Movies.metascore,
                Movies.imdb_rating,
                Movies.imdb_votes,
                Movies.imdb_id,
                Recommendations.type.label("recommendation_type")
            )
            .join(Recommendations, Recommendations.movie_id == Movies.id)
            .filter(Recommendations.user_id == user.id)
            .all()
        )

        movie_responses = [
            {
                "id": movie_id,
                "title": title,
                "lb_movie_id": lb_movie_id,
                "year": year,
                "rated": rated,
                "released": released,
                "runtime": runtime,
                "genre": genre,
                "director": director,
                "writer": writer,
                "actors": actors,
                "plot": plot,
                "language": language,
                "country": country,
                "awards": awards,
                "poster": poster,
                "metascore": metascore,
                "imdb_rating": imdb_rating,
                "imdb_votes": imdb_votes,
                "imdb_id": imdb_id,
                "recommendation_type": recommendation_type
            }
            for (
                movie_id, title, lb_movie_id, year, rated, released, runtime, genre,
                director, writer, actors, plot, language, country, awards, poster,
                metascore, imdb_rating, imdb_votes, imdb_id, recommendation_type
            ) in results
        ]
        
        return movie_responses
        
@app.get("/lb_check/{lb_username}")
async def lb_check(lb_username: str):
    return {"status" : check_lb_user_exists(lb_username)}

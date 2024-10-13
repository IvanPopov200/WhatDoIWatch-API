from fastapi import FastAPI, BackgroundTasks
from helpers import generate_movie_ideas, scrape_user_movies
from dotenv import load_dotenv
from models import Movies, SessionLocal, Users

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
            if user.status in ['scraping', 'movie_data']:
                scraped_count = len(db.query(Movies).filter(Movies.user_id == user.id).all())
                return {"status" : user.status, "len" : scraped_count}


@app.get("/generate/{lb_username}/{analysis_type}")
async def generate(lb_username : str, analysis_type : str, background_tasks: BackgroundTasks):


    background_tasks.add_task(generate_movie_ideas, lb_username, analysis_type)

    return {"status" : "analysis_started"}




from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
DATABASE_NAME = os.getenv("DATABASE_NAME", "your_db_name")
DATABASE_USER = os.getenv("DATABASE_USER", "your_db_user")
DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD", "your_db_password")

SQLALCHEMY_DATABASE_URL = f"mysql+mysqlconnector://{DATABASE_USER}:{DATABASE_PASSWORD}@{DATABASE_HOST}/{DATABASE_NAME}"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class RecommendedMovie(BaseModel):
    title: str

class MovieRecommendations(BaseModel):
    input_movies: List[str]
    recommended_movies: List[RecommendedMovie]

class Movies(Base):
    __tablename__ = 'movies'
    id = Column(Integer, primary_key=True)
    name = Column(String(255))

class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    lb_username = Column(String(255))

class RatedMovies(Base):
    __tablename__ = 'rated_movies'
    id = Column(Integer, primary_key = True)
    title = Column(String(255))
    imdb_id = Column(Integer)
    rating = Column(Integer)

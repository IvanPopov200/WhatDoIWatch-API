from pydantic import BaseModel
from typing import List
from sqlalchemy import Column, Integer, String, Column, Integer, String, Text, DECIMAL, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import Index
from sqlalchemy.ext.declarative import declarative_base
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
    title = Column(String(255), nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    year = Column(String(4), nullable=True)
    rated = Column(String(10), nullable=True)
    released = Column(String(50), nullable=True)
    runtime = Column(String(20), nullable=True)
    genre = Column(String(255), nullable=True)
    director = Column(String(255), nullable=True)
    writer = Column(String(255), nullable=True)
    actors = Column(String(255), nullable=True)
    plot = Column(Text, nullable=True)
    language = Column(String(100), nullable=True)
    country = Column(String(100), nullable=True)
    awards = Column(String(255), nullable=True)
    poster = Column(String(255), nullable=True)
    metascore = Column(String(10), nullable=True)
    imdb_rating = Column(DECIMAL(3, 1), nullable=True)
    imdb_votes = Column(String(20), nullable=True)
    imdb_id = Column(String(20), nullable=True)
    type = Column(String(50), nullable=True)
    dvd = Column(String(50), nullable=True)
    box_office = Column(String(50), nullable=True)
    production = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)

    __table_args__ = (
        Index('movie_id_user_id', 'user_id'),
    )

class Users(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key = True)
    lb_username = Column(String(255))
    status = Column(String(255))

class RatedMovies(Base):
    __tablename__ = 'rated_movies'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    movie_id = Column(Integer, ForeignKey('movies.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    rating = Column(Integer)
    
    __table_args__ = (
        Index('movie_ref', 'movie_id'),
        Index('user_ref', 'user_id')
    )

class Queue(Base):
    __tablename__ = 'queue'
    id = Column(Integer, primary_key = True)
    type = Column(String(255))
    data = Column(Text)
    status = Column(Integer)


import ast
import os
import re

from fastapi import FastAPI, HTTPException
from mysql.connector import connect, Error
from pydantic import BaseModel


app = FastAPI()
try:
    connection = connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PWD", "root"),
        database="rick_and_morty",
    )
except Error as e:
    print(f"Got following error while connecting to rick_and_morty database: {e}")


def fetchall_results(query) -> list:
    """
    Fetch all records in a table
    :param query: sql query to be executed
    :return: list of records
    """
    try:
        results = execute_query(query)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error while fetching records: {e}")
    else:
        return results


def execute_query(query) -> list:
    """
    Execute query
    :param query: sql query to be executed
    :return: list of records
    """
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    return results


# episodes api
@app.get("/episodes")
def get_all_episodes() -> list:
    """
    Get all episodes' info
    :return: list of episodes info
    """
    select_all_episodes_query = "SELECT * FROM episodes"
    results = fetchall_results(select_all_episodes_query)
    return [
        {
            "id": id,
            "name": name,
            "air_date": air_date,
            "episode": episode,
            "characters": ast.literal_eval(characters),
        }
        for id, name, air_date, episode, characters in results
    ]


# characters api
@app.get("/characters")
def get_all_characters() -> list:
    """
    Get all characters' info
    :return: list of characters' info
    """
    select_all_characters_query = "SELECT * FROM characters"
    results = fetchall_results(select_all_characters_query)
    return [
        {
            "id": id,
            "name": name,
            "status": status,
            "species": species,
            "type": type,
            "gender": gender,
            "episode": ast.literal_eval(episode),
        }
        for id, name, status, species, type, gender, episode in results
    ]


# users api
class User(BaseModel):
    username: str
    password: str


class UpdatePassword(BaseModel):
    old_password: str
    new_password: str


@app.get("/users")
def get_all_users() -> list:
    """
    Get all users
    :return: list of users
    """
    select_all_users_query = "SELECT username FROM users"
    results = fetchall_results(select_all_users_query)
    return [result[0] for result in results]


@app.post("/users")
def create_user(user: User) -> str:
    """
    Create user
    :param user: user config
    :return: username
    """
    pat = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")
    if re.fullmatch(pat, user.password) is None:
        raise HTTPException(
            status_code=400,
            detail="Password must have minimum eight characters, at least one uppercase letter, one lowercase letter, one number and one special character.",
        )
    select_username_query = f"SELECT username FROM users WHERE username = '{user.username}'"
    users = fetchall_results(select_username_query)
    if users:
        raise HTTPException(status_code=409, detail="User exists.")
    insert_user_query = f"INSERT INTO users (username, password) VALUES ('{user.username}', '{user.password}')"
    fetchall_results(insert_user_query)
    return user.username


@app.get("/users/{username}")
def get_user(username: str) -> dict:
    """
    Get user
    :param username: username
    :return: dict of username
    """
    select_username_query = f"SELECT username FROM users WHERE username = '{username}'"
    users = fetchall_results(select_username_query)
    if not users:
        raise HTTPException(status_code=404, detail="User does not exist.")
    return {"username": users[0][0]}


@app.put("/users/{username}")
def update_user(username: str, body: UpdatePassword) -> dict:
    """
    Update user
    :param username: username
    :param body: request body
    :return: username
    """
    pat = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$")
    if re.fullmatch(pat, body.new_password) is None:
        raise HTTPException(
            status_code=400,
            detail="New password must have minimum eight characters, at least one uppercase letter, one lowercase letter, one number and one special character.",
        )
    select_user_query = f"SELECT * FROM users WHERE username = '{username}'"
    users = fetchall_results(select_user_query)
    if not users:
        raise HTTPException(status_code=404, detail="User does not exist.")
    if users[0][1] != body.old_password:
        raise HTTPException(status_code=400, detail="Old password is not correct")
    update_user_query = f"UPDATE users SET password = '{body.new_password}' WHERE username = '{username}'"
    fetchall_results(update_user_query)
    return {"username": username}


@app.delete("/users/{username}")
def delete_user(username: str) -> str:
    """
    Delete user
    :param username: username
    :return: delete message
    """
    select_username_query = f"DELETE FROM users WHERE username = '{username}'"
    fetchall_results(select_username_query)
    return f"{username} has been deleted."

import ast
import os
import re
from datetime import timedelta, datetime
from typing import Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from jose import jwt, JWTError
from mysql.connector import connect, Error
from pydantic import BaseModel

from fastapi_pagination import Page, add_pagination, paginate

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
app = FastAPI()
try:
    connection = connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PWD", "root"),
        database=os.getenv("DB_NAME", "rick_and_morty"),
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
        results = execute_query_and_fetch_all(query)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error while fetching records: {e}")
    else:
        return results


def insert_into_table(query) -> int:
    """
    Insert a record into a table
    :param query: sql query to be executed
    :return: id
    """
    try:
        record_id = execute_query_and_return_id(query)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error while inserting record: {e}")
    else:
        return record_id


def execute_query_and_fetch_all(query) -> list:
    """
    Execute query
    :param query: sql query to be executed
    :return: list of records
    """
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    connection.commit()
    return results


def execute_query_and_return_id(query) -> int:
    """
    Execute query and return last id
    :param query: sql query to be executed
    :return: id
    """
    cursor = connection.cursor()
    cursor.execute(query)
    record_id = cursor.lastrowid
    connection.commit()
    return record_id


# users api
SECRET_KEY = "ec19d5ef70c59aa77ac7a98ae47e2b9c1de31b9eae435cde874aaa4cd9a97f6d"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class User(BaseModel):
    username: str
    password: str


class UpdatePassword(BaseModel):
    old_password: str
    new_password: str


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def authenticate_user(username: str, password: str):
    select_username_query = f"SELECT * FROM users WHERE username = '{username}'"
    users = fetchall_results(select_username_query)
    if not users:
        return False
    username_in_db, password_in_db = users[0]
    if password_in_db != password:
        return False
    return User(username=username_in_db, password=password_in_db)


async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    select_username_query = f"SELECT * FROM users WHERE username = '{token_data.username}'"
    users = fetchall_results(select_username_query)
    if users is None:
        raise credentials_exception
    username_in_db, password_in_db = users[0]
    return User(username=username_in_db, password=password_in_db)


@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}


@app.get("/users")
def get_all_users(current_user: User = Depends(get_current_user)) -> list:
    """
    Get all users
    :return: list of users
    """
    select_all_users_query = "SELECT username FROM users"
    results = fetchall_results(select_all_users_query)
    return [result[0] for result in results]


@app.post("/users")
def create_user(user: User, current_user: User = Depends(get_current_user)) -> str:
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
def get_user(username: str, current_user: User = Depends(get_current_user)) -> dict:
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
def update_user(username: str, body: UpdatePassword, current_user: User = Depends(get_current_user)) -> dict:
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
def delete_user(username: str, current_user: User = Depends(get_current_user)) -> str:
    """
    Delete user
    :param username: username
    :return: delete message
    """
    select_username_query = f"DELETE FROM users WHERE username = '{username}'"
    fetchall_results(select_username_query)
    return f"{username} has been deleted."


# episodes api
class Episode(BaseModel):
    id: int
    name: str
    air_date: str
    episode: str
    characters: list


@app.get("/episodes")
def get_all_episodes(current_user: User = Depends(get_current_user)) -> list:
    """
    Get all episodes' info
    :return: list of episodes' info
    """
    select_all_episodes_query = "SELECT * FROM episodes"
    results = fetchall_results(select_all_episodes_query)
    return [
        Episode(id=id, name=name, air_date=air_date, episode=episode, characters=ast.literal_eval(characters))
        for id, name, air_date, episode, characters in results
    ]


# characters api
class Character(BaseModel):
    id: int
    name: str
    status: str
    species: str
    type: str
    gender: str
    episode: list


@app.get("/characters", response_model=Page[Character])
def get_all_characters(
    status: Optional[str] = None,
    species: Optional[str] = None,
    type: Optional[str] = None,
    gender: Optional[str] = None,
    episode_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
):
    """
    Get all characters' info
    :return: page of characters' info
    """
    select_all_characters_query = "SELECT * FROM characters"
    filters = {}
    if status:
        filters["status"] = status
    if species:
        filters["species"] = species
    if type:
        filters["type"] = type
    if gender:
        filters["gender"] = gender
    if episode_id:
        filters["episode_id"] = episode_id
    if filters:
        select_all_characters_query += " WHERE"
        for key, value in filters.items():
            if key == "episode_id":
                select_all_characters_query += f" JSON_CONTAINS(episode, '{episode_id}', '$') AND"
            else:
                select_all_characters_query += f" {key}='{value}' AND"
        select_all_characters_query = select_all_characters_query[:-4]

    results = fetchall_results(select_all_characters_query)
    characters = [
        Character(
            id=id,
            name=name,
            status=status,
            species=species,
            type=type,
            gender=gender,
            episode=ast.literal_eval(episode),
        )
        for id, name, status, species, type, gender, episode in results
    ]
    return paginate(characters)


# comments api
class CommentBody(BaseModel):
    comment: str


class Comment(BaseModel):
    id: int
    username: str
    episode_id: Optional[int]
    character_id: Optional[int]
    comment: str

    class Config:
        validate_assignment = True


@app.post("/comments/episodes/{episode_id}")
def create_comment_episode(body: CommentBody, episode_id: int, current_user: User = Depends(get_current_user)) -> int:
    """
    Create comment on an episode
    :param episode_id: episode id
    :param body: body config
    :return: comment_id
    """
    select_user_exists_query = f"SELECT EXISTS(SELECT username FROM users WHERE username = '{current_user.username}')"
    if fetchall_results(select_user_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Username does not exist.")
    select_episode_id_exists_query = f"SELECT EXISTS(SELECT id FROM episodes WHERE id = '{episode_id}')"
    if fetchall_results(select_episode_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Episode does not exist.")
    insert_comment_query = f"INSERT INTO comments (username, episode_id, comment) VALUES ('{current_user.username}', '{episode_id}', '{body.comment}')"
    return insert_into_table(insert_comment_query)


@app.post("/comments/characters/{character_id}")
def create_comment_character(
    body: CommentBody, character_id: int, current_user: User = Depends(get_current_user)
) -> int:
    """
    Create comment on a character
    :param character_id: character id
    :param body: body config
    :return: comment_id
    """
    select_user_exists_query = f"SELECT EXISTS(SELECT username FROM users WHERE username = '{current_user.username}')"
    if fetchall_results(select_user_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Username does not exist.")
    select_character_id_exists_query = f"SELECT EXISTS(SELECT id FROM characters WHERE id = '{character_id}')"
    if fetchall_results(select_character_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Episode does not exist.")
    insert_comment_query = f"INSERT INTO comments (username, character_id, comment) VALUES ('{current_user.username}', '{character_id}', '{body.comment}')"
    return insert_into_table(insert_comment_query)


@app.post("/comments/episodes/{episode_id}/{character_id}")
def create_comment_on_character_in_episode(
    body: CommentBody, episode_id: int, character_id: int, current_user: User = Depends(get_current_user)
) -> int:
    """
    Create comment on an episode
    :param character_id: character id
    :param episode_id: episode id
    :param body: body config
    :return: comment_id
    """
    select_user_exists_query = f"SELECT EXISTS(SELECT username FROM users WHERE username = '{current_user.username}')"
    if fetchall_results(select_user_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Username does not exist.")
    select_episode_id_exists_query = f"SELECT EXISTS(SELECT id FROM episodes WHERE id = '{episode_id}')"
    if fetchall_results(select_episode_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Episode does not exist.")
    select_characters_in_episode_query = f"SELECT characters FROM episodes WHERE id = '{episode_id}'"
    results = fetchall_results(select_characters_in_episode_query)
    if not results or character_id not in ast.literal_eval(results[0][0]):
        raise HTTPException(status_code=404, detail=f"Character id {character_id} is not in episode id {episode_id}.")
    insert_comment_query = f"INSERT INTO comments (username, episode_id, character_id, comment) VALUES ('{current_user.username}', '{episode_id}', '{character_id}', '{body.comment}')"
    return insert_into_table(insert_comment_query)


@app.put("/comments/{comment_id}")
def update_comment_by_id(comment_id: int, body: CommentBody, current_user: User = Depends(get_current_user)):
    """
    Update comment by id
    :param comment_id: comment id
    :param body: request body
    :return: updated comment info
    """
    select_comment_id_exists_query = f"SELECT EXISTS(SELECT id FROM comments WHERE id = '{comment_id}')"
    if fetchall_results(select_comment_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Comment does not exist.")
    update_comment_query = f"UPDATE comments SET comment = '{body.comment}' WHERE id = '{comment_id}'"
    fetchall_results(update_comment_query)
    select_comment_query = f"SELECT * FROM comments WHERE id = '{comment_id}'"
    results = fetchall_results(select_comment_query)
    id, username, episode_id, character_id, comment = results[0]
    return Comment(
        id=id,
        username=username,
        episode_id=episode_id,
        character_id=character_id,
        comment=comment,
    )


@app.get("/comments", response_model=Page[Comment])
def get_all_comments(username: Optional[str] = None, current_user: User = Depends(get_current_user)):
    """
    Get all comments
    :return: page of comments
    """
    select_all_comments_query = f"SELECT * FROM comments"
    if username:
        select_all_comments_query += f" WHERE username='{username}'"
    results = fetchall_results(select_all_comments_query)
    comments = [
        Comment(
            id=id,
            username=username,
            episode_id=episode_id,
            character_id=character_id,
            comment=comment,
        )
        for id, username, episode_id, character_id, comment in results
    ]
    return paginate(comments)


@app.get("/comments/episodes/{episode_id}", response_model=Page[Comment])
def get_all_comments_of_an_episode(
    episode_id: int, username: Optional[str] = None, current_user: User = Depends(get_current_user)
):
    """
    Get all comments of an episode
    :param username:
    :param episode_id: episode id
    :return: page of comments
    """
    select_episode_id_exists_query = f"SELECT EXISTS(SELECT id FROM episodes WHERE id = '{episode_id}')"
    if fetchall_results(select_episode_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Episode does not exist.")
    select_all_comments_of_episode_query = f"SELECT * FROM comments WHERE episode_id = '{episode_id}'"
    if username:
        select_all_comments_of_episode_query += f" AND username='{username}'"
    results = fetchall_results(select_all_comments_of_episode_query)
    comments = [
        Comment(
            id=id,
            username=username,
            episode_id=episode_id,
            character_id=character_id,
            comment=comment,
        )
        for id, username, episode_id, character_id, comment in results
    ]
    return paginate(comments)


@app.get("/comments/characters/{character_id}", response_model=Page[Comment])
def get_all_comments_of_a_character(
    character_id: int, username: Optional[str] = None, current_user: User = Depends(get_current_user)
):
    """
    Get all comments of a character
    :param username:
    :param character_id: character id
    :return: page of comments
    """
    select_character_id_exists_query = f"SELECT EXISTS(SELECT id FROM characters WHERE id = '{character_id}')"
    if fetchall_results(select_character_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Character does not exist.")
    select_all_comments_of_character_query = f"SELECT * FROM comments WHERE character_id = '{character_id}'"
    if username:
        select_all_comments_of_character_query += f" AND username='{username}'"
    results = fetchall_results(select_all_comments_of_character_query)
    comments = [
        Comment(
            id=id,
            username=username,
            episode_id=episode_id,
            character_id=character_id,
            comment=comment,
        )
        for id, username, episode_id, character_id, comment in results
    ]
    return paginate(comments)


@app.get("/comments/episodes/{episode_id}/{character_id}", response_model=Page[Comment])
def get_all_comments_of_character_in_episode(
    episode_id: int, character_id: int, username: Optional[str] = None, current_user: User = Depends(get_current_user)
):
    """
    Get all comments of a character in an episode
    :param username:
    :param character_id: character id
    :param episode_id: episode id
    :return: page of comments
    """
    select_episode_id_exists_query = f"SELECT EXISTS(SELECT id FROM episodes WHERE id = '{episode_id}')"
    if fetchall_results(select_episode_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Episode does not exist.")
    select_characters_in_episode_query = f"SELECT characters FROM episodes WHERE id = '{episode_id}'"
    results = fetchall_results(select_characters_in_episode_query)
    if not results or character_id not in ast.literal_eval(results[0][0]):
        raise HTTPException(status_code=404, detail=f"Character id {character_id} is not in episode id {episode_id}.")
    select_all_comments_of_character_in_episode_query = (
        f"SELECT * FROM comments WHERE episode_id = '{episode_id}' AND character_id = '{character_id}'"
    )
    if username:
        select_all_comments_of_character_in_episode_query += f" AND username='{username}'"
    results = fetchall_results(select_all_comments_of_character_in_episode_query)
    comments = [
        Comment(
            id=id,
            username=username,
            episode_id=episode_id,
            character_id=character_id,
            comment=comment,
        )
        for id, username, episode_id, character_id, comment in results
    ]
    return paginate(comments)


@app.get("/comments/{comment_id}")
def get_comment_by_id(comment_id: int, current_user: User = Depends(get_current_user)):
    """
    Get comment by id
    :param comment_id: comment id
    :return: comment info
    """
    select_comment_id_exists_query = f"SELECT EXISTS(SELECT id FROM comments WHERE id = '{comment_id}')"
    if fetchall_results(select_comment_id_exists_query)[0][0] == 0:
        raise HTTPException(status_code=404, detail="Comment does not exist.")
    select_comment_query = f"SELECT * FROM comments WHERE id = '{comment_id}'"
    results = fetchall_results(select_comment_query)
    id, username, episode_id, character_id, comment = results[0]
    return Comment(
        id=id,
        username=username,
        episode_id=episode_id,
        character_id=character_id,
        comment=comment,
    )


@app.delete("/comments/{comment_id}")
def delete_comment_by_id(comment_id: int, current_user: User = Depends(get_current_user)) -> str:
    """
    Delete comment by id
    :param comment_id: comment id
    :return: delete message
    """
    select_comment_query = f"DELETE FROM comments WHERE id = '{comment_id}'"
    fetchall_results(select_comment_query)
    return f"Comment id {comment_id} has been deleted."


add_pagination(app)


if __name__ == "__main__":
    uvicorn.run("main:app")

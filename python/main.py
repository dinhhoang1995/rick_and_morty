import ast
import os

from fastapi import FastAPI, HTTPException
from mysql.connector import connect, Error

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


def fetchall_records_in_table(query) -> list:
    """
    Fetch all records in a table
    :param query: sql query to be executed
    :return: list of records
    """
    cursor = connection.cursor()
    cursor.execute(query)
    results = cursor.fetchall()
    return results


@app.get("/episodes")
def get_all_episodes() -> list:
    """
    Get all episodes' info
    :return: list of episodes info
    """
    select_all_episodes_query = "SELECT * FROM episodes"
    try:
        results = fetchall_records_in_table(select_all_episodes_query)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error while fetching records: {e}")
    else:
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


@app.get("/characters")
def get_all_characters() -> list:
    """
    Get all characters' info
    :return: list of characters' info
    """
    select_all_characters_query = "SELECT * FROM characters"
    try:
        results = fetchall_records_in_table(select_all_characters_query)
    except Error as e:
        raise HTTPException(status_code=500, detail=f"Error while fetching records: {e}")
    else:
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

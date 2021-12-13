import json

from mysql.connector import connect, Error
import os


# connect to mysql and create database
try:
    connection = connect(
        host=os.getenv("DB_HOST", "localhost"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PWD", "root"),
    )
except Error as e:
    print(f"Got following error while connecting to mysql: {e}")
else:
    # create database
    drop_db_query = "DROP DATABASE IF EXISTS rick_and_morty"
    create_db_query = "CREATE DATABASE rick_and_morty"
    try:
        with connection.cursor() as cursor:
            cursor.execute(drop_db_query)
            cursor.execute(create_db_query)
        print("Database rick_and_morty has been successfully created.")
    except Error as e:
        print(f"Got following error while creating database: {e}")

# connect to rick_and_morty database and create tables
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
else:
    # episodes table
    create_episodes_table_query = """
        CREATE TABLE episodes(
            id INT NOT NULL AUTO_INCREMENT,
            name VARCHAR(100),
            air_date VARCHAR(100),
            episode VARCHAR(100),
            characters JSON,
            PRIMARY KEY (id)
        )
        """

    # characters table
    create_characters_table_query = """
        CREATE TABLE characters(
            id INT NOT NULL AUTO_INCREMENT,
            name VARCHAR(100),
            status VARCHAR(100),
            species VARCHAR(100),
            type VARCHAR(100),
            gender VARCHAR(100),
            episode JSON,
            PRIMARY KEY (id)
        )
        """

    # users table
    create_users_table_query = """
        CREATE TABLE users(
            username VARCHAR(100) NOT NULL,
            password CHAR(100),
            PRIMARY KEY (username)
        )
        """

    # comments table
    create_comments_table_query = """
        CREATE TABLE comments(
            id INT NOT NULL AUTO_INCREMENT,
            username VARCHAR(100),
            episode_id INT,
            character_id INT,
            comment LONGTEXT,
            PRIMARY KEY (id)
        )
        """

    # episodes records
    insert_episodes_query = """
        INSERT INTO episodes
        (name, air_date, episode, characters)
        VALUES ( %s, %s, %s, %s )
        """
    episodes_records = []
    episodes_list = json.load(
        open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "source", "rick_morty-episodes_v1.json"))
    )
    for episode in episodes_list:
        episodes_records.append(
            (episode.get("name"), episode.get("air_date"), episode.get("episode"), str(episode.get("characters")))
        )

    # characters records
    insert_characters_query = """
        INSERT INTO characters
        (name, status, species, type, gender, episode)
        VALUES ( %s, %s, %s, %s, %s, %s )
        """
    characters_records = []
    characters_list = json.load(
        open(os.path.join(os.path.dirname(os.path.realpath(__file__)), "source", "rick_morty-characters_v1.json"))
    )
    for character in characters_list:
        characters_records.append(
            (
                character.get("name"),
                character.get("status"),
                character.get("species"),
                character.get("type"),
                character.get("gender"),
                str(character.get("episode")),
            )
        )

    try:
        with connection.cursor() as cursor:
            # create episodes table
            cursor.execute("""DROP TABLE IF EXISTS episodes""")
            cursor.execute(create_episodes_table_query)
            print("Episodes table has been successfully created.")

            # create characters table
            cursor.execute("""DROP TABLE IF EXISTS characters""")
            cursor.execute(create_characters_table_query)
            print("Characters table has been successfully created.")

            # create users table
            cursor.execute("""DROP TABLE IF EXISTS users""")
            cursor.execute(create_users_table_query)
            print("Users table has been successfully created.")

            # create comments table
            cursor.execute("""DROP TABLE IF EXISTS comments""")
            cursor.execute(create_comments_table_query)
            print("Comments table has been successfully created.")

            # Insert episodes records to episodes table
            cursor.executemany(insert_episodes_query, episodes_records)
            print("Episodes records have been inserted.")

            # Insert characters records to characters table
            cursor.executemany(insert_characters_query, characters_records)
            print("Characters records have been inserted.")

            connection.commit()
    except Error as e:
        print(f"Got following error while creating tables: {e}")

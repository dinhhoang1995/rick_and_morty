import os
from asyncio import Future

import pytest
from fastapi.testclient import TestClient
from mysql.connector import Error, connect

from python.main import app

connection = connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PWD", "root"),
    database=os.getenv("TEST_DB_NAME", "rick_and_morty_test"),
)

cursor = connection.cursor()
cursor.executemany(
    "INSERT INTO episodes (id, name,air_date, episode, characters ) VALUES (%s, %s,%s, %s, %s)",
    [
        (1, "Pilot", "December 2, 2013", "S01E01", "[1,2]"),
        (2, "Pilot2", "December 3, 2013", "S01E02", "[3,4]"),
    ],
)

cursor.executemany(
    "INSERT INTO characters (id, name,status, species, type, gender , episode) VALUES (%s, %s,%s, %s, %s, %s, %s)",
    [
        (1, "Bob", "Alive", "Human", "", "Male", "[1,2]"),
        (2, "Alice", "Dead", "Alien", "Superwoman", "Female", "[1,3]"),
    ],
)


app.set_db_connection(connection)

client = TestClient(app)


class TestMainApi:
    @pytest.fixture()
    def access_token(self):
        response = client.post(
            "/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="username=admin&password=Abcd1234*",
        )
        assert response.status_code == 200
        return response.json()["access_token"]

    class TestGetAllEpisodes:
        def test_get_all_episodes(self, access_token):
            response = client.get("/episodes", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 200
            assert response.json() == [
                {"id": 1, "name": "Pilot", "air_date": "December 2, 2013", "episode": "S01E01", "characters": [1, 2]},
                {"id": 2, "name": "Pilot2", "air_date": "December 3, 2013", "episode": "S01E02", "characters": [3, 4]},
            ]

        def test_get_all_episodes_error(self, mocker, access_token):
            mock_exc = Future()
            mock_exc.set_exception(Error("fake message"))
            mocker.patch(
                "python.main.execute_query_and_fetch_all",
                side_effect=mock_exc,
            )
            response = client.get("/episodes", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 500
            assert response.json()["detail"] == "Error while fetching records: fake message"

    class TestGetAllCharacters:
        def test_get_all_characters(self, access_token):
            response = client.get("/characters", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 1,
                        "name": "Bob",
                        "status": "Alive",
                        "species": "Human",
                        "type": "",
                        "gender": "Male",
                        "episode": [1, 2],
                    },
                    {
                        "id": 2,
                        "name": "Alice",
                        "status": "Dead",
                        "species": "Alien",
                        "type": "Superwoman",
                        "gender": "Female",
                        "episode": [1, 3],
                    },
                ],
                "total": 2,
                "page": 1,
                "size": 50,
            }

        def test_get_all_characters_error(self, mocker, access_token):
            mock_exc = Future()
            mock_exc.set_exception(Error("fake message"))
            mocker.patch(
                "python.main.execute_query_and_fetch_all",
                side_effect=mock_exc,
            )
            response = client.get("/characters", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 500
            assert response.json()["detail"] == "Error while fetching records: fake message"

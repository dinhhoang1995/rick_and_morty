import os
import subprocess
from asyncio import Future

import pytest
from fastapi.testclient import TestClient
from mysql.connector import Error, connect

from python.main import app

database_name = os.getenv("TEST_DB_NAME", "rick_and_morty_test")

subprocess.run(["python", "../../import_episodes_characters.py", "-n", database_name, "--test"])

connection = connect(
    host=os.getenv("DB_HOST", "localhost"),
    port=int(os.getenv("DB_PORT", "3306")),
    user=os.getenv("DB_USER", "root"),
    password=os.getenv("DB_PWD", "root"),
    database=database_name,
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

    class TestEpisodes:
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

    class TestCharacters:
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

        def test_get_all_characters_with_filters(self, access_token):
            response = client.get(
                "/characters?status=Alive&species=Human&gender=Male&episode_id=1&page=1&siz=50",
                headers={"Authorization": f"Bearer {access_token}"},
            )
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
                    }
                ],
                "total": 1,
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

    class TestUsers:
        def test_get_all_users(self, access_token):
            response = client.get("/users", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 200
            assert response.json() == ["admin"]

        def test_create_user_password_error(self, access_token):
            response = client.post(
                "/users",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"username": "dhtran", "password": "toto"},
            )
            assert response.status_code == 400
            assert (
                response.json()["detail"]
                == "Password must have minimum eight characters, at least one uppercase letter, one lowercase letter, one number and one special character."
            )

        def test_create_user_success(self, access_token):
            response = client.post(
                "/users",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"username": "dhtran", "password": "Azerty123*"},
            )
            assert response.status_code == 201
            assert response.text == '"dhtran"'

        def test_create_user_duplicated(self, access_token):
            response = client.post(
                "/users",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"username": "dhtran", "password": "Azerty123*"},
            )
            assert response.status_code == 409
            assert response.json()["detail"] == "User exists."

        def test_get_user_not_found(self, access_token):
            response = client.get("/users/toto", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 404
            assert response.json()["detail"] == "User does not exist."

        def test_get_user_success(self, access_token):
            response = client.get("/users/dhtran", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 200
            assert response.json() == {"username": "dhtran"}

        def test_update_user_password_error(self, access_token):
            response = client.put(
                "/users/dhtran",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"old_password": "Azerty123*", "new_password": "toto"},
            )
            assert response.status_code == 400
            assert (
                response.json()["detail"]
                == "New password must have minimum eight characters, at least one uppercase letter, one lowercase letter, one number and one special character."
            )

        def test_update_user_not_found(self, access_token):
            response = client.put(
                "/users/toto",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"old_password": "Azerty123*", "new_password": "Xyzabc123*"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "User does not exist."

        def test_update_user_old_password_error(self, access_token):
            response = client.put(
                "/users/dhtran",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"old_password": "toto", "new_password": "Xyzabc123*"},
            )
            assert response.status_code == 400
            assert response.json()["detail"] == "Old password is not correct."

        def test_update_user_success(self, access_token):
            response = client.put(
                "/users/dhtran",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"old_password": "Azerty123*", "new_password": "Xyzabc123*"},
            )
            assert response.status_code == 200
            assert response.json() == {"username": "dhtran"}

        def test_delete_user_success(self, access_token):
            response = client.delete("/users/dhtran", headers={"Authorization": f"Bearer {access_token}"})
            assert response.status_code == 204
            assert response.text == '"dhtran has been deleted."'

    class TestComments:
        def test_create_comment_episode_not_found(self, access_token):
            response = client.post(
                "/comments/episodes/100",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Episode does not exist."

        def test_create_comment_episode_internal_error(self, mocker, access_token):
            mock_exc = Future()
            mock_exc.set_exception(Error("fake message"))
            mocker.patch(
                "python.main.execute_query_and_return_id",
                side_effect=mock_exc,
            )
            response = client.post(
                "/comments/episodes/1",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 500
            assert response.json()["detail"] == "Error while inserting record: fake message"

        def test_create_comment_episode_success(self, access_token):
            response = client.post(
                "/comments/episodes/1",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 201
            assert response.text == "1"

        def test_create_comment_character_not_found(self, access_token):
            response = client.post(
                "/comments/characters/1000",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Character does not exist."

        def test_create_comment_character_success(self, access_token):
            response = client.post(
                "/comments/characters/1",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 201
            assert response.text == "2"

        def test_create_comment_on_character_in_episode_episode_not_found(self, access_token):
            response = client.post(
                "/comments/episodes/100/1",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Episode does not exist."

        def test_create_comment_on_character_in_episode_character_not_found(self, access_token):
            response = client.post(
                "/comments/episodes/1/100",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Character id 100 is not in episode id 1."

        def test_create_comment_on_character_in_episode_success(self, access_token):
            response = client.post(
                "/comments/episodes/1/1",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 201
            assert response.text == "3"

        def test_update_comment_by_id_not_found(self, access_token):
            response = client.put(
                "/comments/10",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a comment"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Comment does not exist."

        def test_update_comment_by_id_success(self, access_token):
            response = client.put(
                "/comments/1",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"comment": "This is a new comment"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "id": 1,
                "username": "admin",
                "episode_id": 1,
                "character_id": None,
                "comment": "This is a new comment",
            }

        def test_get_all_comments_success(self, access_token):
            response = client.get(
                "/comments",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 1,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": None,
                        "comment": "This is a new comment",
                    },
                    {
                        "id": 2,
                        "username": "admin",
                        "episode_id": None,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 3,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_with_filter_on_existent_username(self, access_token):
            response = client.get(
                "/comments?username=admin",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 1,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": None,
                        "comment": "This is a new comment",
                    },
                    {
                        "id": 2,
                        "username": "admin",
                        "episode_id": None,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 3,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_with_filter_on_non_existent_username(self, access_token):
            response = client.get(
                "/comments?username=toto",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [],
                "total": 0,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_of_an_episode_not_found(self, access_token):
            response = client.get(
                "/comments/episodes/100",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Episode does not exist."

        def test_get_all_comments_of_an_episode_success(self, access_token):
            response = client.get(
                "/comments/episodes/1",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 1,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": None,
                        "comment": "This is a new comment",
                    },
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 2,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_of_an_episode_with_filter_success(self, access_token):
            response = client.get(
                "/comments/episodes/1?username=admin",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 1,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": None,
                        "comment": "This is a new comment",
                    },
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 2,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_of_a_character_not_found(self, access_token):
            response = client.get(
                "/comments/characters/1000",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Character does not exist."

        def test_get_all_comments_of_a_character_success(self, access_token):
            response = client.get(
                "/comments/characters/1",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 2,
                        "username": "admin",
                        "episode_id": None,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 2,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_of_a_character_with_filter_success(self, access_token):
            response = client.get(
                "/comments/characters/1?username=admin",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 2,
                        "username": "admin",
                        "episode_id": None,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 2,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_of_character_in_episode_episode_not_found(self, access_token):
            response = client.get(
                "/comments/episodes/100/1",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Episode does not exist."

        def test_get_all_comments_of_character_in_episode_character_not_found(self, access_token):
            response = client.get(
                "/comments/episodes/1/1000",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Character id 1000 is not in episode id 1."

        def test_get_all_comments_of_character_in_episode_success(self, access_token):
            response = client.get(
                "/comments/episodes/1/1",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 1,
                "page": 1,
                "size": 50,
            }

        def test_get_all_comments_of_character_in_episode_with_filter_success(self, access_token):
            response = client.get(
                "/comments/episodes/1/1?username=admin",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "items": [
                    {
                        "id": 3,
                        "username": "admin",
                        "episode_id": 1,
                        "character_id": 1,
                        "comment": "This is a comment",
                    },
                ],
                "total": 1,
                "page": 1,
                "size": 50,
            }

        def test_get_comment_by_id_not_found(self, access_token):
            response = client.get(
                "/comments/100",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 404
            assert response.json()["detail"] == "Comment does not exist."

        def test_get_comment_by_id_success(self, access_token):
            response = client.get(
                "/comments/1",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 200
            assert response.json() == {
                "id": 1,
                "username": "admin",
                "episode_id": 1,
                "character_id": None,
                "comment": "This is a new comment",
            }

        def test_delete_comment_by_id_success(self, access_token):
            response = client.delete(
                "/comments/3",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            assert response.status_code == 204
            assert response.text == '"Comment id 3 has been deleted."'

from asyncio import Future

from fastapi.testclient import TestClient
from mysql.connector import Error

from python.main import app

client = TestClient(app)


class TestMainApi:
    class TestGetAllEpisodes:
        def test_get_all_episodes(self, mocker):
            mocker.patch(
                "python.main.execute_query_and_fetch_all",
                return_value=[
                    (1, "Pilot", "December 2, 2013", "S01E01", "[1,2]"),
                    (2, "Pilot2", "December 3, 2013", "S01E02", "[3,4]"),
                ],
            )
            response = client.get("/episodes")
            assert response.status_code == 200
            assert response.json() == [
                {"id": 1, "name": "Pilot", "air_date": "December 2, 2013", "episode": "S01E01", "characters": [1, 2]},
                {"id": 2, "name": "Pilot2", "air_date": "December 3, 2013", "episode": "S01E02", "characters": [3, 4]},
            ]

        def test_get_all_episodes_error(self, mocker):
            mock_exc = Future()
            mock_exc.set_exception(Error("fake message"))
            mocker.patch(
                "python.main.execute_query_and_fetch_all",
                side_effect=mock_exc,
            )
            response = client.get("/episodes")
            assert response.status_code == 500
            assert response.json()["detail"] == "Error while fetching records: fake message"

    class TestGetAllCharacters:
        def test_get_all_characters(self, mocker):
            mocker.patch(
                "python.main.execute_query_and_fetch_all",
                return_value=[
                    (1, "Bob", "Alive", "Human", "", "Male", "[1,2]"),
                    (2, "Alice", "Dead", "Alien", "Superwoman", "Female", "[1,3]"),
                ],
            )
            response = client.get("/characters")
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

        def test_get_all_characters_error(self, mocker):
            mock_exc = Future()
            mock_exc.set_exception(Error("fake message"))
            mocker.patch(
                "python.main.execute_query_and_fetch_all",
                side_effect=mock_exc,
            )
            response = client.get("/characters")
            assert response.status_code == 500
            assert response.json()["detail"] == "Error while fetching records: fake message"

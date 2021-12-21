# rick_and_morty
Jellysmack technical test

## Pull and run mysql with dockerdocker pull mysql

Pull mysql docker image
```commandline
docker pull mysql
```

Run mysql database in docker container and expose port 3306
```commandline
docker run -p 3306:3306 --name mysql -e MYSQL_ROOT_PASSWORD=root -d mysql:latest
```

## Install requirements and format files
Install requirements with the following cml:
```commandline
pip3 install -q -r requirements.txt
```
Install tests requirements with the following cml:
```commandline
pip3 install -q -r tests_requirements.txt
```
Format files with the following cml:
```commandline
black -l 120 python import_episodes_characters.py
```

## Set environment variables
Set database host:
```commandline
export DB_HOST="localhost"
```
Set database port:
```commandline
export DB_HOST=3306
```
Set database user:
```commandline
export DB_USER="root"
```
Set database user password:
```commandline
export DB_PWD="root"
```
Set database name:
```commandline
export DB_NAME="rick_and_morty"
```
Set test database name:
```commandline
export TEST_DB_NAME="rick_and_morty_test"
```
## Create database and add tables
Run script with following cml:
```commandline
python import_episodes_characters.py -n rick_and_morty
```

## Run API server
In python directory, run the server with:
```commandline
python main.py
```
Connect to Swagger UI at:
```commandline
http://127.0.0.1:8000/docs
```

## Run pytest
In root folder, run tests with:
```commandline
pytest --cov-report term --cov=python python/tests
```

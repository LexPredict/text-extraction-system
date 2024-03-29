# Text Extraction System

## Development Environment
### Project Structure

This project consists of two parts:
 - The text extraction system (web api + celery), the backend;
 - Common data transfer objects (DTO) which may be used both at the backend and at the python API client side.
An http API client in Python is also bundled together with the DTO classes.
Both backend and DTO+client are in the same git repo but in different folders.

The development should go in the same virtual env. The API client does not have its special requirements.txt file 
but there is only setup.py file to be able to install it via pip right from git.

### Requirements
The base was developed on:
- Ubuntu 20.04
- Python 3.8.5
- Docker 19.03.13

It may work on other versions of the software.

### Setting-up Development Environment

#### 1. Clone project repo
```
git clone https://github.com/LexPredict/text-extraction-system.git
cd ./text-extraction-system
``` 
#### 2. Ensure there is the proper Python 3 version installed.
```
/usr/bin/python3 -v
```
Install the compatible Python version using the official installation instructions if needed.
#### 3. Install required system libraries and Setup Python virtual environment
```
./prepare_dev_env_ubuntu_20_04_python_3_8.sh
```
Or use the appropriate script for the OS and Python version you are working with. 
#### 5. Prepare project config files
```
cp ./docker/deploy/setenv_local.local_dev_example.sh ./docker/deploy/setenv_local.sh
cp .env.local_dev_example .env
cp .test_env.local_dev_example .test_env
```
Check/update the configuration files contents if needed.
#### 6. Deploy Postgres and other required third-party software to the local Docker Swarm cluster
```
sudo docker -v
```
You need to create a swarm-scoped network before the stack is deployed, so create it if it doesn't already exist.
```
sudo docker network create --driver overlay contraxsuite_contrax_net
```
and then
```
sudo docker swarm init

cd ./docker/deploy
sudo ./deploy-to-swarm-cluster.sh
``` 

### Starting Local Dev Server
```
source venv/bin/activate

# start web api
uvicorn text_extraction_system.web_api:app --reload

# start celery
celery -A text_extraction_system.tasks worker
```
The same commands can be used to start web api and celery in PyCharm.

### Updating Python packages
`Pipdeptree` is used to check all dependencies and generate file with all requirements:
```
pipdeptree -f | sed 's/ //g' | sort -u > requirements.txt
```

### Compiling .proto files
```shell
python -m grpc_tools.protoc -I ../text_extraction_system_api/text_extraction_system_api/proto_files --python_out=../text_extraction_system_api/text_extraction_system_api/python_pb2_files ../text_extraction_system_api/text_extraction_system_api/proto_files/*.proto
```

### Running Unit Tests
```
cd text_extraction_system
source venv/bin/activate
pytest --log-cli-level=INFO text_extraction_system
```
The unit tests do not (should not) require the .env/.test_env files.

### Running Integration Tests
The integration test require running WebAPI and Celery apps.
They connect to the existing system playing the role of the API client and pass the full text extraction cycle.

Terminal session 1:
```
source venv/bin/activate
# start web api
uvicorn text_extraction_system.web_api:app --reload
```
Terminal session 2:
```
source venv/bin/activate
# start web api
celery -A text_extraction_system.tasks worker
```
Terminal session 3:
```
source venv/bin/activate
pytest --log-cli-level=INFO integration_tests/
```

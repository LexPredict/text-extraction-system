# Text Extraction System

## Development Environment
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
#### 3. Install required system libraries
```
./install_ubuntu_requirements.sh
``` 
#### 4. Setup Python virtual environment
```
virtualenv -p /usr/bin/python3 venv
source venv/bin/activate
pip install -r requirements.txt
``` 
#### 5. Prepare project config files
```
cp ./docker/setenv_local.local_dev_example.sh ./docker/setenv_local.sh
cp .env.local_dev_example .env
cp .test_env.local_dev_example
```
Check/update the configuration files contents if needed.
#### 6. Deploy Postgres and other required third-party software to the local Docker Swarm cluster
```
sudo docker -v
sudo docker swarm init

cd ./docker/deploy
sudo ./deploy-to-swarm-cluster.sh
``` 

### Running Unit Tests
```
cd text_extraction_system
source venv/bin/activate
pytest text_extraction_system
```

### Starting Local Dev Server
```
source venv/bin/activate

```



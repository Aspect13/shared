#   Copyright 2022 getcarrier.io
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

from os import environ
from datetime import datetime
from typing import Union
from urllib.parse import urlparse

LOCAL_DEV = True

# ALLOWED_EXTENSIONS = ['zip', 'py']
CURRENT_RELEASE = 'latest'
REDIS_USER = environ.get('REDIS_USER', '')
REDIS_PASSWORD = environ['REDIS_PASSWORD']
REDIS_HOST = environ['REDIS_HOST']
REDIS_PORT = environ.get('REDIS_PORT', 6379)
REDIS_DB = environ.get('REDIS_DB', 2)
RABBIT_HOST = environ['RABBIT_HOST']
RABBIT_USER = environ['RABBITMQ_USER']
RABBIT_PASSWORD = environ['RABBITMQ_PASSWORD']
RABBIT_PORT = environ.get('RABBIT_PORT', 5672)
RABBIT_QUEUE_NAME = environ.get('RABBIT_QUEUE_NAME', 'default')
APP_HOST = environ['APP_HOST']
GF_API_KEY = environ.get('GF_API_KEY', '')
INFLUX_PASSWORD = environ.get('INFLUX_PASSWORD', '')
INFLUX_USER = environ.get('INFLUX_USER', '')
INFLUX_PORT = environ.get('INFLUX_PORT', 8086)
LOKI_PORT = environ.get('LOKI_PORT', 3100)
_url = urlparse(APP_HOST)
EXTERNAL_LOKI_HOST = f"http://{_url.netloc.split('@')[1]}" if "@" in APP_HOST else APP_HOST.replace("https://", "http://")
INTERNAL_LOKI_HOST = "http://carrier-loki"
APP_IP = urlparse(EXTERNAL_LOKI_HOST).netloc
MINIO_ENDPOINT = environ.get('MINIO_HOST', 'http://carrier-minio:9000')
MINIO_ACCESS = environ.get('MINIO_ACCESS_KEY', 'admin')
MINIO_SECRET = environ.get('MINIO_SECRET_KEY', 'password')
MINIO_REGION = environ.get('MINIO_REGION', 'us-east-1')
# LOKI_HOST = environ.get('LOKI', f'{EXTERNAL_LOKI_HOST}:3100')
MAX_DOTS_ON_CHART = 100
VAULT_URL = environ.get('VAULT_URL', 'http://carrier-vault:8200')
VAULT_DB_PK = 1
ADMINISTRATION_MODE = 'administration'
VAULT_ADMINISTRATION_NAME = ADMINISTRATION_MODE
DEFAULT_MODE = 'default'
GRID_ROUTER_URL = environ.get("GRID_ROUTER_URL", f"{EXTERNAL_LOKI_HOST}:4444/quota")


# def allowed_file(filename):
#     return '.' in filename and \
#            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# UNZIP_DOCKERFILE = """FROM kubeless/unzip:latest
# ADD {localfile} /tmp/{docker_path}
# ENTRYPOINT ["unzip", "/tmp/{docker_path}", "-d", "/tmp/unzipped"]
# """


# UNZIP_DOCKER_COMPOSE = """version: '3'
# services:
#   unzip:
#     build: {path}
#     volumes:
#       - {volume}:/tmp/unzipped
#     labels:
#       - 'traefik.enable=false'
#     container_name: unzip-{task_id}
# volumes:
#   {volume}:
#     external: true
# """

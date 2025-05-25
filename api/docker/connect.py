from api.config.vm import *
import docker

docker_client = docker.DockerClient(base_url=f"tcp://{PRIMARY_HOST['host']}:{PRIMARY_HOST['port']}")
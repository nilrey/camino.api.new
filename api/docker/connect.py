from api.config.vm import *
import docker

docker_client = docker.DockerClient(base_url=f"tcp://{PRIMERY_HOST['host']}:{PRIMERY_HOST['port']}")
from api.config.vm import *
import docker

docker_client = docker.DockerClient(base_url=f"tcp://{VIRTUAL_MACHINES_LIST[0]['host']}:{VIRTUAL_MACHINES_LIST[0]['port']}")
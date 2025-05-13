import docker

client = docker.DockerClient(base_url='tcp://10.0.0.2:2375')

def list_images():
    """Получить список образов"""
    return client.images()

def list_containers(all=True):
    """Получить список контейнеров"""
    return client.containers(all=all)

def create_container(image: str, name: str = None, ports: dict = None, environment: dict = None):
    """Создать контейнер"""

    container = client.containers.create(
        image="10.0.0.1:6000/bytetracker-image",
        command=[
            "--input_data", '{"det_path": "../weights/yolov8n.pt", "epochs": 2, "device": "gpu"}',
            "--host_web", "http://10.0.0.1:8000"
        ],
        #runtime="nvidia",  
        shm_size="20g",
        volumes={
            "/family/video": {"bind": "/family/video", "mode": "rw"},
            "/family/projects_data/bae0b840-1c3f-11f0-82d2-0242ac140003/9f9e112e-2caf-11f0-be61-0242ac140002/markups_out": {"bind": "/output", "mode": "rw"},
            "/family/projects_data/bae0b840-1c3f-11f0-82d2-0242ac140003/bae82dd2-1c3f-11f0-82d2-0242ac140003/videos": {"bind": "/input_videos", "mode": "rw"},
            "/family/weights/weights_tracker": {"bind": "/weights/", "mode": "rw"},
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            "/family/projects_data/bae0b840-1c3f-11f0-82d2-0242ac140003/9f9e112e-2caf-11f0-be61-0242ac140002/markups_in": {"bind": "/input_data", "mode": "rw"},
            "/family/projects_data": {"bind": "/projects_data", "mode": "rw"}
        },
        # remove=True,       
        detach=True,       
        tty=True           
    )


    # print(f"Container {container.name} started with ID {container.id}")
    # print(container.logs())  # если контейнер уже завершил работу


    # port_bindings = {}
    # exposed_ports = []

    # if ports:
    #     for container_port, host_port in ports.items():
    #         port_bindings[container_port] = host_port
    #         exposed_ports.append(container_port)

    # host_config = client.create_host_config(
    #     port_bindings=port_bindings if ports else None
    # )

    # container = client.create_container(
    #     image=image,
    #     name=name,
    #     ports=exposed_ports if exposed_ports else None,
    #     environment=[f"{k}={v}" for k, v in (environment or {}).items()],
    #     host_config=host_config
    # )
    return container.id

def start_container(container_id: str):
    """Запустить контейнер"""
    container = client.containers.get(container_id)
    container.start()
    return {"status": "started"}

def remove_container(container_id: str, force=True):
    """Удалить контейнер"""
    client.remove_container(container=container_id, force=force)
    return {"status": "removed"}

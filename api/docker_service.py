import docker

client = docker.DockerClient(base_url='tcp://172.17.0.1:2375')

container = client.containers.run(
    "center-php",
    #command="sleep 5",
    detach=True,  # запустить в фоне
    name="center_php_test"
)

print(f"Container {container.name} started with ID {container.id}")
print(container.logs())  # если контейнер уже завершил работу

def list_images():
    """Получить список образов"""
    return client.images()

def list_containers(all=True):
    """Получить список контейнеров"""
    return client.containers(all=all)

def create_container(image: str, name: str = None, ports: dict = None, environment: dict = None):
    """Создать контейнер"""
    port_bindings = {}
    exposed_ports = []

    if ports:
        for container_port, host_port in ports.items():
            port_bindings[container_port] = host_port
            exposed_ports.append(container_port)

    host_config = client.create_host_config(
        port_bindings=port_bindings if ports else None
    )

    container = client.create_container(
        image=image,
        name=name,
        ports=exposed_ports if exposed_ports else None,
        environment=[f"{k}={v}" for k, v in (environment or {}).items()],
        host_config=host_config
    )
    return container

def start_container(container_id: str):
    """Запустить контейнер"""
    client.start(container=container_id)
    return {"status": "started"}

def remove_container(container_id: str, force=True):
    """Удалить контейнер"""
    client.remove_container(container=container_id, force=force)
    return {"status": "removed"}

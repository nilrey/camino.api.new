import os
from docker.types import DeviceRequest
from docker.errors import NotFound, APIError
import docker
import socket
import logging
from datetime import datetime
from typing import List, Dict
from api.config.config import *
from api.config.vm import *
import api.config.hosts as IP
from .docker.connect import docker_client

log_dir = '/export/logs'
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = os.path.join(log_dir, f"{timestamp}_api_back_new.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        # logging.StreamHandler()  # Чтобы лог также отображался в консоли
    ]
)



def get_docker_images() -> List[Dict]:
    logging.info("Start get_docker_images")
    images_info = []
    vm = PRIMARY_HOST # берем только ВМ , где располагается репозиторий образов ИНС
    # for vm in C.VIRTUAL_MACHINES_LIST:
    try:
        if is_host_reachable(vm['host']):
            client = docker.DockerClient(base_url=f"tcp://{vm['host']}:{vm['port']}")
            images = client.images.list()
            for image in images:
                image_tags = image.tags if image.tags else ["<none>:<none>"]
                for tag in image_tags:
                    if ":" in tag:
                        name, tag_part = tag.rsplit(":", 1)
                    else:
                        name, tag_part = tag, "<none>"
                    if name in BLOCK_LIST_IMAGES:
                        continue

                    location = 'registry'  if IP.HOST_REGISTRY in name and vm["name"] else vm["name"]
                    images_info.append({
                        "id": image.id.replace("sha256:", ""),
                        "name": name,
                        "tag": tag_part,
                        "location": location,
                        "created_at": image.attrs.get("Created", ""),
                        "size": image.attrs.get("Size", 0),
                        "comment": image.attrs.get("Comment", ""),
                        "archive": ""
                    })
            client.close()
    except Exception as e:
        logging.error(f"Ошибка при подключении к {vm['name']} ({vm['host']}): {e}")
    return images_info

def find_image_by_id(image_id: str):
    try:
        images = get_docker_images()
        for image in images:
            logging.info(f'{image.get("id")} {image_id}')
            if image.get("id") == image_id:
                logging.info(f"Image {image_id} found on VM: {image.get('location')}")
                return image
    except Exception as e:
        logging.error(f"Error retrieving images from VM {image.get('location')}: {e}")
    return None

def find_container_by_id(container_id: str):
    try:
        containers = get_docker_containers()
        for container in containers:
            logging.info(f'{container.get("id")} {container_id}')
            if container.get("id") == container_id:
                logging.info(f"Container {container_id} found on VM: {container.get('host')}")
                return container
    except Exception as e:
        logging.error(f"Ошибка в поиске контейнера: {e}")
    return None

def get_docker_containers() -> List[Dict]:
    containers_info = []
    for vm in VIRTUAL_MACHINES_LIST:
        try: 
            client = docker.DockerClient(base_url=f"tcp://{vm['host']}:{vm['port']}")
            containers = client.containers.list()
            for container in containers:
                command = container.attrs['Config']['Cmd']
                command_str = " ".join(command) if isinstance(command, list) else str(command)

                ports = container.attrs['NetworkSettings']['Ports']
                ports_str = ", ".join([
                    f"{container_port}" for container_port in ports.keys() if ports
                ]) if ports else ""

                status = get_uptime_string(container.attrs['Created']) if container.status == 'running' else container.status

                container_info = {
                    "id": container.id,
                    "host": vm['host'],
                    "image": {
                        "id": container.image.id.replace("sha256:", ""),
                        "name": container.image.tags[0].split(":")[0] if container.image.tags else "",
                        "tag": container.image.tags[0].split(":")[1] if container.image.tags else ""
                    },
                    "command": command_str,
                    "names": container.name,
                    "ports": ports_str,
                    "created_at": container.attrs['Created'],
                    "status": status
                }
                containers_info.append(container_info)
        except Exception as e:
            logging.error(f"Error connecting to {vm['host']}: {str(e)}")
    return containers_info

def run_container(params): 
    vm_host, is_error = get_available_vm() 
    if is_error:
        message = f'Ошибка при просмотре списка VM: {vm_host}'
    elif vm_host:
        logging.info(f'params: {params}')
        client = docker.DockerClient(base_url=f'tcp://{vm_host}:2375', timeout=5) 
        image = find_image_by_id(params["imageId"]) # '10.0.0.1:6000/bytetracker-image'  #params["imageId"]
        name = params["name"]
        command = [
            "--input_data", params['hyper_params'],
            "--host_web", IP.HOST_ANN
        ]
        command.append('--work_format_training') if params['ann_mode'] == 'teach' else None

        volumes = {
            f'/family{params["video_storage"]}': {"bind": "/family/video", "mode": "rw"},
            f'/family{params["out_dir"]}': {"bind": "/output", "mode": "rw"},
            f'/family{params["in_dir"]}': {"bind": "/input_videos", "mode": "rw"},
            f'/family{params["weights"]}': {"bind": "/weights/", "mode": "rw"},
            f'/family{params["markups"]}': {"bind": "/input_data", "mode": "rw"},
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            "/family/projects_data": {"bind": "/projects_data", "mode": "rw"}
        }

        # Формируем строку запуска для лога
        volume_args = ' '.join([f'-v {host}:{opt["bind"]}:{opt["mode"]}' for host, opt in volumes.items()])
        command_str = f"docker run --gpus all --shm-size=20g --name {name} {volume_args} {image} {' '.join(command)}"
        logging.info(f"{command_str}")

        # Используем device_requests для GPU
        
        device_requests = []
        if not DEBUG_MODE:
            device_requests = [
                DeviceRequest(count=-1, capabilities=[['gpu']])
            ]

        # Запуск контейнера
        container = client.containers.run(
            image=image['name'],
            name=name,
            command=command,
            device_requests=device_requests,
            shm_size="20g",
            volumes=volumes,
            # remove=True,
            detach=True,
            tty=True
        )


        logging.info(f'Контейнер запущен на: {vm_host}')
        message = container.id
        logging.info(f'Контейнер id: {container.id}')
    else:
        message = 'Нет свободных VM.'
        logging.info(message)
    
    return message

def create_start_container(params): 
    vm_host, is_error = get_available_vm() 
    if is_error:
        message = f'Ошибка при просмотре списка VM: {vm_host}'
    elif vm_host:

        logging.info(f'params: {params}')
        client = docker.DockerClient(base_url=f'tcp://{vm_host}:2375', timeout=5) 
        image = find_image_by_id(params["imageId"])
        name = params["name"]
        command = [
            "--input_data", params['hyper_params'],
            "--host_web", IP.HOST_ANN
        ]
        if params['ann_mode'] == 'teach':
            command.append('--work_format_training')

        volumes = {
            f'/family{params["video_storage"]}': {"bind": "/family/video", "mode": "rw"},
            f'/family{params["out_dir"]}': {"bind": "/output", "mode": "rw"},
            f'/family{params["in_dir"]}': {"bind": "/input_videos", "mode": "rw"},
            f'/family{params["weights"]}': {"bind": "/weights/", "mode": "rw"},
            f'/family{params["markups"]}': {"bind": "/input_data", "mode": "rw"},
            "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            "/family/projects_data": {"bind": "/projects_data", "mode": "rw"}
        }

        # Формируем строку запуска для логирования
        volume_args = ' '.join([f'-v {host}:{opt["bind"]}:{opt["mode"]}' for host, opt in volumes.items()])
        command_str = f"docker run --gpus all --shm-size=20g --name {name} {volume_args} {image} {' '.join(command)}"
        logging.info(f"{command_str}")

        device_requests = []
        if not DEBUG_MODE:
            device_requests = [DeviceRequest(count=-1, capabilities=[['gpu']])]

        container = client.containers.create(
            image=image['name'],
            name=name,
            command=command,
            tty=True,
            stdin_open=True,
            detach=True,
            auto_remove=True,                 
            shm_size="20g",                   
            volumes=volumes,
            device_requests=device_requests
        )

        container.start()

        logging.info(f'Контейнер запущен')
        message = container.id

    else:
        message = 'Нет свободных VM.'
        logging.info(message)
    
    return message

def stop_container(container_id: str):
    is_error = True
    message = ""
    try:
        container = find_container_by_id(container_id)
        if container :
            client = docker.DockerClient(base_url=f'tcp://{container["host"]}:2375', timeout=5) 
            container = client.containers.get(container_id)
            container.stop(timeout=0)  # Или container.kill() для жёсткой остановки
            message = f"Контейнер {container_id} успешно остановлен."
            logging.info(message)
            is_error = False
        else:
            message = f"Контейнер с ID {container_id} не найден."
            logging.info(message)
    except APIError as e:
        message = f"Ошибка Docker API: {e.explanation}" 
        logging.error(message)
    except Exception as e:
        message = f"Произошла непредвиденная ошибка: {e}"
        logging.exception(message)
    
    # if is_error :
    #     container = find_container_by_id(container_id)

    return {"error": is_error, "message": message}

def is_host_reachable(ip, port=2375, timeout=3):
    """ проверяем если вирт. машина доступна, доп. ставим таймаут 
    """
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error):
        return False

def check_vm_containers(vm_host, ann_images) -> bool:
    """ на виртуальной машине vm_host ищем контейнер созданный из образа в списке ann_images.
    если найдено хоть одно название из ann_images, то выходим из цикла - данная машина занята (True)
    иначе - возвращаем False
    """
    if not is_host_reachable(vm_host):
        logging.error(f"{vm_host} недоступен")
        return True  # превышен таймаут подключение считаем, что VM можно пропустить
        
    try:
        # Подключение к удаленному Docker Engine API
        client = docker.DockerClient(base_url=f'tcp://{vm_host}:2375', timeout=5) 
        containers = client.containers.list()

        has_ann_image = False

        for container in containers:
            image_tags = container.image.tags or [container.image.short_id]
            for tag in image_tags:
                for ann_image in ann_images:
                    if ann_image in tag:
                        has_ann_image = True
                        break
                if has_ann_image:
                    break

        client.close()
        return has_ann_image

    except Exception as e:
        logging.error(f'Ошибка при подключении к {vm_host}: {e}')
        # Возвращаем True, чтобы не останавливать перебор
        return True

def get_available_vm():
    is_error = True
    try:
        if not VIRTUAL_MACHINES_LIST:
            message = 'Список виртуальных машин пуст.'
        elif not ANN_IMAGES_LIST:
            message = 'Список ИНС образов пуст.'
        else:
            for vm in VIRTUAL_MACHINES_LIST:
                logging.info(f"Проверка {vm['name']} [{vm['host']}]")
                has_ann_image = check_vm_containers(vm['host'], ANN_IMAGES_LIST)
                if not has_ann_image:
                    is_error = False
                    logging.error(f"VM {vm['host']} свободна.")
                    return vm['host'], is_error
            message = 'Все виртуальные машины заняты.'
    except Exception as e:
        message = f'Ошибка find_vm_without_ann_images: {e}'
        
    logging.error(message) if is_error else logging.info(message)

    return message , is_error


def get_uptime_string(created_at):
    """Преобразует время создания контейнера в строку формата 'Up X minutes'"""
    created_datetime = datetime.strptime(created_at.split('.')[0], '%Y-%m-%dT%H:%M:%S')
    uptime = datetime.utcnow() - created_datetime
    total_seconds = int(uptime.total_seconds())
    
    if total_seconds < 60:
        return "Up less than a minute"
    
    minutes = total_seconds // 60
    
    if minutes < 60:
        return f"Up {minutes} minute{'s' if minutes != 1 else ''}"
    
    hours = minutes // 60
    remaining_minutes = minutes % 60
    
    if hours < 24:
        if remaining_minutes == 0:
            return f"Up {hours} hour{'s' if hours != 1 else ''}"
        return f"Up {hours} hour{'s' if hours != 1 else ''} {remaining_minutes} minute{'s' if remaining_minutes != 1 else ''}"
    
    days = hours // 24
    remaining_hours = hours % 24
    
    if remaining_hours == 0:
        return f"Up {days} day{'s' if days != 1 else ''}"
    return f"Up {days} day{'s' if days != 1 else ''} {remaining_hours} hour{'s' if remaining_hours != 1 else ''}"
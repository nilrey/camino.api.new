import os
import docker
from docker.types import DeviceRequest
from docker.errors import NotFound, APIError
import socket
import logging
from datetime import datetime
from typing import List, Dict
from api.config.vm import *
import api.config.hosts as IP

log_dir = '/home/ubuntu/Documents/back/logs'
os.makedirs(log_dir, exist_ok=True)

timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
log_filename = os.path.join(log_dir, f"vm_checker_{timestamp}.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        # logging.StreamHandler()  # Чтобы лог также отображался в консоли
    ]
)

client = docker.DockerClient(base_url=f"tcp://{VIRTUAL_MACHINES_LIST[0]['host']}:{VIRTUAL_MACHINES_LIST[0]['port']}")



def get_docker_images() -> List[Dict]:
    images_info = []
    for vm in VIRTUAL_MACHINES_LIST:
        try:
            client = docker.DockerClient(base_url=f"tcp://{vm['host']}:{vm['port']}")
            images = client.images.list()
            for image in images:
                image_tags = image.tags if image.tags else ["<none>:<none>"]
                for tag in image_tags:
                    name, tag_part = tag.split(":") if ":" in tag else (tag, "<none>")
                    images_info.append({
                        "id": image.id,
                        "name": name,
                        "tag": tag_part,
                        "location": vm["name"],
                        "created_at": image.attrs.get("Created", ""),
                        "size": image.attrs.get("Size", 0),
                        "comment": image.attrs.get("Comment", ""),
                        "archive": ""  # Заполните при необходимости
                    })
            client.close()
        except Exception as e:
            logging.error(f"Ошибка при подключении к {vm['name']} ({vm['host']}): {e}")
    return images_info


def list_images(): 
    return client.images()


def list_running_containers() -> List[Dict]:
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

                container_info = {
                    "id": container.id,
                    "host": vm['host'],
                    "image": {
                        "id": container.image.id,
                        "name": container.image.tags[0].split(":")[0] if container.image.tags else "",
                        "tag": container.image.tags[0].split(":")[1] if container.image.tags else ""
                    },
                    "command": command_str,
                    "names": container.name,
                    "ports": ports_str,
                    "created_at": container.attrs['Created'],
                    "status": container.status
                }
                containers_info.append(container_info)
        except Exception as e:
            logging.error(f"Error connecting to {vm['host']}: {str(e)}")
    return containers_info


def list_containers(all=True): 
    return client.containers(all=all)

def run_container(params): 
    vm_ip, is_error = find_vm_without_ann_images() 
    if is_error:
        message = f'Ошибка при просмотре списка VM: {vm_ip}'
    elif vm_ip:
        logging.info(f'params: {params}')
        client = docker.DockerClient(base_url=f'tcp://{vm_ip}:2375', timeout=5) 
        image = '10.0.0.1:6000/bytetracker-image'  #params["imageId"]
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
        device_requests = [
            DeviceRequest(count=-1, capabilities=[['gpu']])
        ]

        # Запуск контейнера
        container = client.containers.run(
            image=image,
            name=name,
            command=command,
            device_requests=device_requests,
            shm_size="20g",
            volumes=volumes,
            remove=True,
            detach=True,
            tty=True
        )


        logging.info(f'Контейнер запущен на: {vm_ip}')
        message = container.id
    else:
        message = 'Нет свободных VM.'
        logging.info(message)
    
    return message

def start_container(container_id: str): 
    try:
        container = client.containers.get(container_id)
        container.start()
        logging.info(f"Контейнер {container_id} успешно запущен.")
    except NotFound:
        logging.warning(f"Контейнер с ID {container_id} не найден.")
    except APIError as e:
        logging.error(f"Ошибка Docker API: {e.explanation}")
    except Exception as e:
        logging.exception(f"Произошла непредвиденная ошибка: {e}")    
    return {"status": "started"}

def stop_container(container_id: str, force=True): 
    try:
        container = client.containers.get(container_id)
        container.stop(timeout=0)  # Или container.kill() для жёсткой остановки
        logging.info(f"Контейнер {container_id} успешно остановлен.")
    except NotFound:
        logging.warning(f"Контейнер с ID {container_id} не найден.")
    except APIError as e:
        logging.error(f"Ошибка Docker API: {e.explanation}")
    except Exception as e:
        logging.exception(f"Произошла непредвиденная ошибка: {e}")
    return {"status": "stopped"}

def is_host_reachable(ip, port=2375, timeout=3):
    try:
        with socket.create_connection((ip, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error):
        return False
    

def check_vm_containers(vm_ip, ann_images):
    if not is_host_reachable(vm_ip):
        logging.error(f"{vm_ip} недоступен")
        return True  # превышен таймаут подключение считаем, что VM можно пропустить
        
    try:
        # Подключение к удаленному Docker Engine API
        client = docker.DockerClient(base_url=f'tcp://{vm_ip}:2375', timeout=5) 
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
        logging.error(f'Ошибка при подключении к {vm_ip}: {e}')
        # Возвращаем True, чтобы не останавливать перебор
        return True

def find_vm_without_ann_images():
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
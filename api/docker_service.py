import docker
import logging
from docker.errors import NotFound, APIError
import os
from datetime import datetime
import socket
from api.config.vm import *

log_dir = '/export/logs'
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

client = docker.DockerClient(base_url='tcp://172.17.0.1:2375')

def list_images(): 
    return client.images()

def list_containers(all=True): 
    return client.containers(all=all)

def run_container(image: str, name: str = None, ports: dict = None, environment: dict = None): 
    vm_ip, is_error = find_vm_without_ann_images() 
    if is_error:
        message = f'Ошибка при просмотре списка VM: {vm_ip}'
    elif vm_ip:
        client = docker.DockerClient(base_url=f'tcp://{vm_ip}:2375', timeout=5) 
        container = client.containers.run(
            # image="10.0.0.1:6000/bytetracker-image",
            image="center-php",
            # command=[
            #     "--input_data", '{"det_path": "../weights/yolov8n.pt", "epochs": 2, "device": "gpu"}',
            #     "--host_web", "http://10.0.0.1:8000"
            # ],
            # #runtime="nvidia",  
            # # shm_size="20g",
            # volumes={
            #     "/family/video": {"bind": "/family/video", "mode": "rw"},
            #     "/family/projects_data/bae0b840-1c3f-11f0-82d2-0242ac140003/9f9e112e-2caf-11f0-be61-0242ac140002/markups_out": {"bind": "/output", "mode": "rw"},
            #     "/family/projects_data/bae0b840-1c3f-11f0-82d2-0242ac140003/bae82dd2-1c3f-11f0-82d2-0242ac140003/videos": {"bind": "/input_videos", "mode": "rw"},
            #     "/family/weights/weights_tracker": {"bind": "/weights/", "mode": "rw"},
            #     "/var/run/docker.sock": {"bind": "/var/run/docker.sock", "mode": "rw"},
            #     "/family/projects_data/bae0b840-1c3f-11f0-82d2-0242ac140003/9f9e112e-2caf-11f0-be61-0242ac140002/markups_in": {"bind": "/input_data", "mode": "rw"},
            #     "/family/projects_data": {"bind": "/projects_data", "mode": "rw"}
            # },
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
        logging.error(f"{vm_ip} недоступен по TCP (порт 2375)")
        return True  # превышен таймаут подключение считаем, что VM можно пропустить
        
    try:
        # Подключение к удаленному Docker Engine API
        client = docker.DockerClient(base_url=f'tcp://{vm_ip}:2375', timeout=5) 
        containers = client.containers.list()

        found_ann_image = False

        for container in containers:
            image_tags = container.image.tags or [container.image.short_id]
            for tag in image_tags:
                for ann_image in ann_images:
                    if ann_image in tag:
                        found_ann_image = True
                        break
                if found_ann_image:
                    break

        client.close()
        return found_ann_image

    except Exception as e:
        logging.error(f'Ошибка при подключении к {vm_ip}: {e}')
        # Возвращаем True, чтобы не останавливать перебор
        return True

def find_vm_without_ann_images():
    # VIRTUAL_MACHINE_LIST = ['10.0.0.1', '10.0.0.2', '10.0.0.3', '10.0.0.4']
    # VIRTUAL_MACHINE_LIST = ['172.17.0.1']
    is_error = True
    try:
        if not VIRTUAL_MACHINE_LIST:
            message = 'Список виртуальных машин пуст.'
        elif not ANN_IMAGES_LIST:
            message = 'Список названий образов пуст.'
        else:
            for vm_ip in VIRTUAL_MACHINE_LIST:
                logging.info(f'Проверка {vm_ip};')
                has_ann_image = check_vm_containers(vm_ip, ANN_IMAGES_LIST)
                if not has_ann_image:
                    is_error = False
                    logging.error(f'VM {vm_ip} свободна.')
                    return vm_ip, is_error
            message = 'Все виртуальные машины содержат хотя бы один контейнер с ИНС или не доступны.'
    except Exception as e:
        message = f'Ошибка find_vm_without_ann_images: {e}'
        
    if is_error:
        logging.error(message)
    else:
         logging.info(message)

    return message , is_error
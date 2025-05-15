from fastapi import HTTPException
from fastapi import APIRouter
from api import docker_service
from api import schemas 
from pydantic import BaseModel
from typing import Optional, Dict
from fastapi import APIRouter, Path
import psycopg2

# Docker Endpoints
router = APIRouter()

@router.get("/docker/images/count")
async def get_images_count():
    version = None
    # try:
    #     conn = psycopg2.connect(
    #         host="10.0.0.1",
    #         database="camino",
    #         user="postgres",
    #         password="postgres"
    #     )
    #     cur = conn.cursor()
    #     cur.execute("SELECT version();")
    #     version = cur.fetchone()
    #     cur.close()
    #     conn.close()
    # except Exception as e:
    #     raise HTTPException(status_code=500, detail=str(e))
    
    images = docker_service.list_images()
    return {"count": len(images), "db_ver:sion": version}

@router.get("/docker/containers/count")
async def get_containers_count():
    containers = docker_service.list_containers(all=True)
    return {"count": len(containers)}

@router.post("/images/{imageId}/run")
async def run_container(request: schemas.CreateContainerRequest , imageId: str = Path(..., description="ID образа Docker")):
    try:
        params = request.model_dump()
        params["imageId"] = imageId # 0d0eb38589601232c9ad9196d1eaa01db2280d7a2377860ecfe0e93883ef53e3
        response = docker_service.run_container(params)
        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/docker/container/start")
async def start_container(request: schemas.ContainerIdRequest):
    try:
        result = docker_service.start_container(container_id=request.container_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/docker/container/stop")
async def stop_container(request: schemas.ContainerIdRequest):
    try:
        result = docker_service.stop_container(container_id=request.container_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/docker/vm/check")
async def get_vm_without_ann():
    result, is_error = docker_service.find_vm_without_ann_images() 
    if is_error:
        message = f'Ошибка при просмотре VM: {result}'
    elif result: 
        message = f'Свободная VM: {result}'
    else:
        message = 'Нет свободных VM.'            

    return {"message": message}
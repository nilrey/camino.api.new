from fastapi import HTTPException
from fastapi import APIRouter
from api import docker_service
from api import schemas 
from pydantic import BaseModel
from typing import Optional, Dict

# Docker Endpoints
router = APIRouter()

@router.get("/docker/images/count")
async def get_images_count():
    images = docker_service.list_images()
    return {"count": len(images)}

@router.get("/docker/containers/count")
async def get_containers_count():
    containers = docker_service.list_containers(all=True)
    return {"count": len(containers)}

@router.post("/docker/container/create")
async def create_container(request: schemas.CreateContainerRequest):
    try:
        container = docker_service.create_container(
            image=request.image,
            name=request.name,
            ports=request.ports,
            environment=request.environment
        )
        return {"container_id": container.get("Id")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/docker/container/start")
async def start_container(request: schemas.ContainerIdRequest):
    try:
        result = docker_service.start_container(container_id=request.container_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/docker/container/remove")
async def remove_container(request: schemas.ContainerIdRequest):
    try:
        result = docker_service.remove_container(container_id=request.container_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

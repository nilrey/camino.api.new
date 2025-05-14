from fastapi import HTTPException
from fastapi import APIRouter
from api import docker_service
from api import schemas 
from pydantic import BaseModel
from typing import Optional, Dict

import psycopg2

# Docker Endpoints
router = APIRouter()

@router.get("/docker/images/count")
async def get_images_count():
    version = None
    try:
        conn = psycopg2.connect(
            host="10.0.0.1",
            database="camino",
            user="postgres",
            password="postgres"
        )
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        cur.close()
        conn.close()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    images = docker_service.list_images()
    return {"count": len(images), "db_ver:sion": version}

@router.get("/docker/containers/count")
async def get_containers_count():
    containers = docker_service.list_containers(all=True)
    return {"count": len(containers)}

@router.post("/docker/container/run")
async def run_container(request: schemas.CreateContainerRequest):
    try:
        container = docker_service.run_container(
            image=request.image,
            name=request.name,
            ports=request.ports,
            environment=request.environment
        )
        return {"container_id": container}
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

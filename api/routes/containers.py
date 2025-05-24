from fastapi import HTTPException
from fastapi import APIRouter, Response, status
from fastapi.responses import JSONResponse
from api import docker_service
from api import schemas 
from pydantic import BaseModel
from typing import Optional, Dict
from fastapi import APIRouter, Path
import psycopg2

# Docker Endpoints
router = APIRouter()


@router.get("/images", tags=["Docker-образы"])
async def list_docker_images():
    try:
        images = docker_service.get_docker_images()
        return JSONResponse(content={
            "pagination": {"totalItems": len(images)},
            "items": images
        })
    except Exception as e:
        return JSONResponse(status_code=500, content={
            "code": 500,
            "message": str(e)
        })

# @router.get("/docker/images/count")
# async def get_images_count():
#     version = None
#     # try:
#     #     conn = psycopg2.connect(
#     #         host="10.0.0.1",
#     #         database="camino",
#     #         user="postgres",
#     #         password="postgres"
#     #     )
#     #     cur = conn.cursor()
#     #     cur.execute("SELECT version();")
#     #     version = cur.fetchone()
#     #     cur.close()
#     #     conn.close()
#     # except Exception as e:
#     #     raise HTTPException(status_code=500, detail=str(e))
    
#     images = docker_service.list_images()
#     return {"count": len(images), "db_ver:sion": version}


@router.get("/images/{image_id}", tags=["Docker-образы"])
async def get_docker_image(image_id: str):
    try:
        image = docker_service.find_image_by_id(image_id)
        if image:
            return {
                "id": image.get("id", ""),
                "name": image.get("name", ""),
                "tag": image.get("tag", ""),
                "location": image.get("location", ""),
                "created_at": image.get("created_at", ""),
                "size": image.get("size", ""),
                "comment": image.get("comment", ""),
                "archive": image.get("archive", "")
            }
        else:
            raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        return {
            "code": 500,
            "message": str(e)
        }


# @router.get("/docker/containers/count")
# async def get_containers_count():
#     containers = docker_service.list_containers(all=True)
#     return {"count": len(containers)}

@router.post("/images/{imageId}/run", tags=["Docker-образы"])
async def run_container(request: schemas.CreateContainerRequest , imageId: str = Path(...)):
    try:
        params = request.model_dump()
        params["imageId"] = imageId # 0d0eb38589601232c9ad9196d1eaa01db2280d7a2377860ecfe0e93883ef53e3
        response = docker_service.create_start_container(params)
        return {"message": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.post("/docker/container/start")
# async def start_container(request: schemas.ContainerIdRequest):
#     try:
#         result = docker_service.start_container(container_id=request.container_id)
#         return result
#     except Exception as e:
#         raise HTTPException(status_code=500, detail=str(e))

@router.get("/containers", tags=["Docker-контейнеры"])
async def get_containers():
    try:
        containers = docker_service.get_docker_containers()
        return {
            "pagination": {
                "totalItems": len(containers)
            },
            "items": containers
        }
    except Exception as e:
        docker_service.logger.error(f"Error retrieving containers: {str(e)}")
        return Response(
            content={
                "code": 500,
                "message": str(e)
            },
            media_type="application/json",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    

@router.get("/containers/{containerId}", tags=["Docker-контейнеры"], summary="Получение информации о Docker-контейнере на сервере")
async def api_docker_container(container_id: str):
    try:
        container = docker_service.find_container_by_id(container_id)
        if container:
            return container
        else:
            raise HTTPException(status_code=404, detail="Image not found")
    except Exception as e:
        return {
            "code": 500,
            "message": str(e)
        }

@router.put("/containers/{containerId}/stop", tags=["Docker-контейнеры"])
async def stop_container(container_id: str = Path(..., alias="containerId")):
    try:
        result = docker_service.stop_container(container_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# @router.get("/containers/{containerId}/stop", tags=["Docker-контейнеры"], summary="Остановка контейнера на сервере")
# async def api_docker_container(container_id: str):
#     try:
#         container = docker_service.find_container_by_id(container_id)
#         if container:
#             result = docker_service.stop_container(container_id=request.container_id)
#             return result
#         else:
#             raise HTTPException(status_code=404, detail="Image not found")
#     except Exception as e:
#         return {
#             "code": 500,
#             "message": str(e)
#         }


@router.get("/vm/check", tags=["Виртуальные машины"])
async def get_vm_without_ann():
    docker_service.logging.info("Начало обработки")
    result, is_error = docker_service.get_available_vm() 
    if is_error:
        message = f'Ошибка при просмотре VM: {result}'
    elif result: 
        message = f'Свободная VM: {result}'
    else:
        message = 'Нет свободных VM.'            

    return {"message": message}
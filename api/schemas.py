from pydantic import BaseModel
from typing import Optional, Dict

class CreateContainerRequest(BaseModel):
    image: str
    name: Optional[str] = None
    ports: Optional[Dict[str, int]] = None
    environment: Optional[Dict[str, str]] = None

class ContainerIdRequest(BaseModel):
    container_id: str

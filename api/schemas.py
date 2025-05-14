from pydantic import BaseModel
from typing import Optional, List

class CreateContainerRequest(BaseModel):
    name: Optional[str] = ""
    ann_mode: Optional[str] = ""
    weights: Optional[str] = ""
    hyper_params: Optional[str] = ""
    in_dir: Optional[str] = ""
    out_dir: Optional[str] = ""
    markups: Optional[str] = ""
    video_storage: Optional[str] = ""
    network: Optional[str] = ""
    dataset_id: Optional[str] = ""
    only_verified_chains: bool = False
    only_selected_files: List[str] = []

class ContainerIdRequest(BaseModel):
    container_id: str

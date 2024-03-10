from pydantic import BaseModel
from typing import List, Optional

class PartChangeoverBase(BaseModel):
    part_name: Optional[str] = None
    
class PartChangeoverCreate(PartChangeoverBase):
    pass

class PartChangeover(PartChangeoverBase):
    id: Optional[int] = None

    class Config:
        orm_mode = True
        
class MatrixUpdate(BaseModel):
    changeover_time: int

class MatrixUpdateMore(BaseModel):
    matrix_id: int
    changeover_time: Optional[int] = None

class MasterPartsChangeoverMatrixBase(BaseModel):
    part_id: Optional[int] = None
    target_part_id: Optional[int] = None
    changeover_time: Optional[int] = None
    part_name: Optional[str] = None
    target_part_name: Optional[str] = None

class MasterPartsChangeoverMatrixCreate(MasterPartsChangeoverMatrixBase):
    pass

class MasterPartsChangeoverMatrix(MasterPartsChangeoverMatrixBase):
    id: Optional[int] = None

    class Config:
        orm_mode = True
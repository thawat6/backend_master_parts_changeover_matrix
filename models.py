from sqlalchemy import  Column, Integer, String, ForeignKey
from sqlalchemy.orm import  relationship
from database import Base

class PartChangeover(Base):
    __tablename__ = 'part_changeover'

    id = Column(Integer, primary_key=True, index=True)
    part_name = Column(String, unique=True, index=True)

class MasterPartsChangeoverMatrix(Base):
    __tablename__ = 'master_parts_changeover_matrix'

    id = Column(Integer, primary_key=True, index=True)
    part_id = Column(Integer, ForeignKey('part_changeover.id'))
    target_part_id = Column(Integer, ForeignKey('part_changeover.id'))
    changeover_time = Column(Integer)

    part = relationship("PartChangeover", foreign_keys=[part_id])
    target_part = relationship("PartChangeover", foreign_keys=[target_part_id])
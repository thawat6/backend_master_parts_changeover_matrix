from fastapi import FastAPI, HTTPException, Depends,Response,status
from sqlalchemy.orm import Session
from sqlalchemy import asc
from sqlalchemy.orm import sessionmaker
import models
from models import PartChangeover as DBPartChangeover, MasterPartsChangeoverMatrix as DBMasterPartsChangeoverMatrix
from schemas import PartChangeover, MasterPartsChangeoverMatrix, MatrixUpdate, PartChangeoverBase,MatrixUpdateMore
from database import engine
from typing import List
from sqlalchemy.exc import IntegrityError
import pandas as pd
from fastapi.middleware.cors import CORSMiddleware

models.Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
app = FastAPI()


origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from sqlalchemy.exc import IntegrityError

def create_part_and_matrix_entry(part_create: PartChangeoverBase, db: Session):
    try:
        new_part = DBPartChangeover(part_name=part_create.part_name)
        db.add(new_part)
        db.commit()
        db.refresh(new_part)
    except IntegrityError:
        new_part = db.query(DBPartChangeover).filter(DBPartChangeover.part_name == part_create.part_name).first()

    try:
        new_matrix_entry = DBMasterPartsChangeoverMatrix(part_id=new_part.id, target_part_id=new_part.id)
        db.add(new_matrix_entry)
        db.commit()
        db.refresh(new_matrix_entry)
    except IntegrityError:
        pass  

    existing_parts = db.query(DBPartChangeover).all()
    
    for existing_part in existing_parts:
        if new_part.id != existing_part.id:
            try:
                new_matrix_entry = DBMasterPartsChangeoverMatrix(part_id=new_part.id, target_part_id=existing_part.id)
                db.add(new_matrix_entry)
                db.commit()
                db.refresh(new_matrix_entry)
            except IntegrityError:
                pass  
            
            try:
                new_matrix_entry = DBMasterPartsChangeoverMatrix(part_id=existing_part.id, target_part_id=new_part.id)
                db.add(new_matrix_entry)
                db.commit()
                db.refresh(new_matrix_entry)
            except IntegrityError:
                pass  

    return new_part

def delete_parts(db: Session, part_id: int):
    references = db.query(models.MasterPartsChangeoverMatrix).filter(
        (models.MasterPartsChangeoverMatrix.part_id == part_id) |
        (models.MasterPartsChangeoverMatrix.target_part_id == part_id)
    ).all()
    
    if references:
        for reference in references:
            db.delete(reference)
        db.commit()
    
    part_to_delete = db.query(models.PartChangeover).filter(models.PartChangeover.id == part_id).first()
    if part_to_delete:
        db.delete(part_to_delete)
        db.commit()
        return {"message": "Part deleted successfully"}
    else:
        return {"message": "Part not found"}
    
@app.post("/parts-and-matrix/", response_model=PartChangeover)
def create_part_and_matrix_entry_api(part_create: PartChangeoverBase, db: Session = Depends(get_db)):
    return create_part_and_matrix_entry(part_create, db)
    
@app.post("/parts/more/")
def update_parts_more(parts_updates: List[PartChangeover], db: Session = Depends(get_db)):
    parts_entries = db.query(DBPartChangeover).all()
    if not parts_updates and parts_entries:
        for parts_item in parts_entries:
            delete_parts(db, parts_item.id)
    elif parts_entries:
        intersect_parts = [item for item in parts_entries if item.id not in [data_item.id for data_item in parts_updates]]
        if intersect_parts:
            for intersect_item in intersect_parts:
                delete_parts(db, intersect_item.id)

    if parts_updates:
        for update in parts_updates:
            part_name = update.part_name
            if not update.id or update.id == 0:
                create_part_and_matrix_entry(update, db)
            else:    
                db_parts = db.query(models.PartChangeover).filter(models.PartChangeover.id == update.id).first()
                if db_parts is None:
                    return create_part_and_matrix_entry(update, db)
                db_parts.part_name = part_name
            db.commit()
            
    return {"status": "Update successful"}

    
@app.get("/matrix/", response_model=List[MasterPartsChangeoverMatrix])
def get_matrix_entries(db: Session = Depends(get_db)):
    matrix_entries = db.query(DBMasterPartsChangeoverMatrix).order_by(asc(DBMasterPartsChangeoverMatrix.id)).all()
    matrix_entries_with_names = []
    for entry in matrix_entries:
        part_name = db.query(DBPartChangeover).filter(DBPartChangeover.id == entry.part_id).first().part_name
        target_part_name = db.query(DBPartChangeover).filter(DBPartChangeover.id == entry.target_part_id).first().part_name
        entry_dict = entry.__dict__
        entry_dict['part_name'] = part_name
        entry_dict['target_part_name'] = target_part_name
        matrix_entries_with_names.append(entry_dict)
    return matrix_entries_with_names

@app.put("/matrix/{matrix_id}")
def update_matrix_entry(matrix_id: int, matrix_update: MatrixUpdate, db: Session = Depends(get_db)):
    changeover_time = matrix_update.changeover_time
    db_matrix_entry = db.query(models.MasterPartsChangeoverMatrix).filter(models.MasterPartsChangeoverMatrix.id == matrix_id).first()
    if db_matrix_entry is None:
        raise HTTPException(status_code=404, detail="Matrix entry not found")
    db_matrix_entry.changeover_time = changeover_time
    db.commit()
    return {"status": "Update successful"}

@app.put("/matrix/more/")
def update_matrix_entries(matrix_updates: List[MatrixUpdateMore], db: Session = Depends(get_db)):
    for update in matrix_updates:
        matrix_id = update.matrix_id
        changeover_time = update.changeover_time
        db_matrix_entry = db.query(models.MasterPartsChangeoverMatrix).filter(models.MasterPartsChangeoverMatrix.id == matrix_id).first()
        if db_matrix_entry is None:
            raise HTTPException(status_code=404, detail=f"Matrix entry with id {matrix_id} not found")
        db_matrix_entry.changeover_time = changeover_time
        db.commit()
    return {"status": "Update successful"}

@app.get("/export/parts/")
def export_matrix_entries_to_excel(response: Response, db: Session = Depends(get_db)):
    parts_entries = db.query(DBPartChangeover).all()
    data = []
    for entry in parts_entries:
        data.append({
            'id': entry.id,
            'part_name': entry.part_name
        })
    df = pd.DataFrame(data)
    
    csv_data = df.to_csv(index=False)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})

@app.get("/export/matrix/")
def export_matrix_entries_to_excel(response: Response, db: Session = Depends(get_db)):
    matrix_entries = db.query(DBMasterPartsChangeoverMatrix).all()
    
    parts = {part.id: part.part_name for part in db.query(DBPartChangeover).all()}
    
    data = []
    for entry in matrix_entries:
        part_name = parts.get(entry.part_id)
        target_part_name = parts.get(entry.target_part_id)
        data.append({
            'part_id': entry.part_id,
            'part_name': part_name,
            'target_part_id': entry.target_part_id,
            'target_part_name': target_part_name,
            'changeover_time': entry.changeover_time,
            'id': entry.id
        })
    
    df = pd.DataFrame(data)
    
    csv_data = df.to_csv(index=False)
    return Response(content=csv_data, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=data.csv"})


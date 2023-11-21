import datetime
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List

import uvicorn
import app.schemas as _schemas
import app.services as _services

app = FastAPI()

# CORS Configuration
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_services.create_database()

# Endpoints for testing
@app.post("/multiple_activityframes/", tags=["Active Testing"], response_model=List[_schemas.ActivityFrame])
def create_multiple_activityframes(requestData: _schemas.ActivityFrameRequest, db: Session = Depends(_services.get_db)):
    created_activityframes = []
    values = requestData.dataFromDevice.split(";")
    groupedValues = [values[i:i+3] for i in range(0, len(values), 3)
                     if len(values[i:i+3]) == 3]

    for group in groupedValues:
        activityFrameData = {
            "patient_id": requestData.patientId,
            "activity_id": group[0],
            "time_started": group[1],
            "time_finished": group[2]
        }
        activityframe = _schemas.ActivityFrameCreate(**activityFrameData)
        created_frame = _services.create_activityframe(db=db, activityframe=activityframe)
        created_activityframes.append(created_frame)

    return created_activityframes

# Endpoints for MedicalPersonel
@app.post("/medicalpersonel/", tags=["Medical Personel"], response_model=_schemas.MedicalPersonel)
def create_medicalpersonel(
    medicalpersonel: _schemas.MedicalPersonelCreate, db: Session = Depends(_services.get_db)
):
    db_medicalpersonel = _services.get_medicalpersonel_by_email(db=db, email=medicalpersonel.email)
    if db_medicalpersonel:
        raise HTTPException(
            status_code=400, detail="Email is already in use"
        )
    return _services.create_medicalpersonel(db=db, medicalpersonel=medicalpersonel)

@app.get("/medicalpersonel/", tags=["Medical Personel"], response_model=List[_schemas.MedicalPersonel])
def read_medicalpersonels(skip: int = 0, limit: int = 10, db: Session = Depends(_services.get_db)):
    medicalpersonels = _services.get_medicalpersonels(db=db, skip=skip, limit=limit)
    return medicalpersonels

@app.get("/medicalpersonel/{medicalpersonel_id}", tags=["Medical Personel"], response_model=_schemas.MedicalPersonel)
def read_medicalpersonel(medicalpersonel_id: int, db: Session = Depends(_services.get_db)):
    db_medicalpersonel = _services.get_medicalpersonel(db=db, medicalpersonel_id=medicalpersonel_id)
    if db_medicalpersonel is None:
        raise HTTPException(
            status_code=404, detail="Medical personel not found"
        )
    return db_medicalpersonel

@app.delete("/medicalpersonel/{medicalpersonel_id}", tags=["Medical Personel"], response_model=_schemas.MedicalPersonel)
def delete_medicalpersonel(medicalpersonel_id: int, db: Session = Depends(_services.get_db)):
    db_medicalpersonel = _services.get_medicalpersonel(db=db, medicalpersonel_id=medicalpersonel_id)
    if db_medicalpersonel is None:
        raise HTTPException(
            status_code=404, detail="Medical personel not found"
        )
    _services.delete_medicalpersonel(db=db, medicalpersonel_id=medicalpersonel_id)
    return db_medicalpersonel

@app.put("/medicalpersonel/{medicalpersonel_id}", tags=["Medical Personel"], response_model=_schemas.MedicalPersonel)
def update_medicalpersonel(medicalpersonel_id: int, medicalpersonel: _schemas.MedicalPersonelCreate, db: Session = Depends(_services.get_db)):
    db_medicalpersonel = _services.get_medicalpersonel(db=db, medicalpersonel_id=medicalpersonel_id)
    if db_medicalpersonel is None:
        raise HTTPException(
            status_code=404, detail="Medical personel not found"
        )
    db_medicalpersonel = _services.update_medicalpersonel(db=db, medicalpersonel_id=medicalpersonel_id, medicalpersonel=medicalpersonel)
    return db_medicalpersonel


# Endpoints for Patient
@app.post("/patients/", tags=["Patient"], response_model=_schemas.Patient)
def create_patient(
    patient: _schemas.PatientCreate, db: Session = Depends(_services.get_db)
):
    db_patient = _services.get_patient_by_email(db=db, email=patient.email)
    if db_patient:
        raise HTTPException(
            status_code=400, detail="Email is already in use"
        )
    return _services.create_patient(db=db, patient=patient)

@app.get("/patients/", tags=["Patient"], response_model=List[_schemas.Patient])
def read_patients(skip: int = 0, limit: int = 10, db: Session = Depends(_services.get_db)):
    patients = _services.get_patients(db=db, skip=skip, limit=limit)
    return patients

@app.get("/patients/{patient_id}", tags=["Patient"], response_model=_schemas.Patient)
def read_patient(patient_id: int, db: Session = Depends(_services.get_db)):
    db_patient = _services.get_patient(db=db, patient_id=patient_id)
    if db_patient is None:
        raise HTTPException(
            status_code=404, detail="Patient not found"
        )
    return db_patient

# Endpoints for Device
@app.post("/devices/", tags=["Device"], response_model=_schemas.Device)
def create_device(
    device: _schemas.DeviceCreate, db: Session = Depends(_services.get_db)
):
    db_device = _services.get_device(db=db, device_id=device.id)
    if db_device:
        raise HTTPException(
            status_code=400, detail="Device with this ID already exists"
        )
    return _services.create_device(db=db, device=device)

@app.get("/devices/", tags=["Device"], response_model=List[_schemas.Device])
def read_devices(skip: int = 0, limit: int = 10, db: Session = Depends(_services.get_db)):
    devices = _services.get_devices(db=db, skip=skip, limit=limit)
    return devices

@app.get("/devices/{device_id}", tags=["Device"], response_model=_schemas.Device)
def read_device(device_id: int, db: Session = Depends(_services.get_db)):
    db_device = _services.get_device(db=db, device_id=device_id)
    if db_device is None:
        raise HTTPException(
            status_code=404, detail="Device not found"
        )
    return db_device

# Endpoints for ActivityFrame
@app.post("/activityframes/", tags=["Activity Frame"], response_model=_schemas.ActivityFrame)
def create_activityframe(
    activityframe: _schemas.ActivityFrameCreate, db: Session = Depends(_services.get_db)
):
    # Create activity frame based on the provided data
    return _services.create_activityframe(db=db, activityframe=activityframe)

@app.get("/activityframes/", tags=["Activity Frame"], response_model=List[_schemas.ActivityFrame])
def read_activityframes(skip: int = 0, limit: int = 10, db: Session = Depends(_services.get_db)):
    activityframes = _services.get_activityframes(db=db, skip=skip, limit=limit)
    return activityframes

@app.get("/activityframes/{activityframe_id}", tags=["Activity Frame"], response_model=_schemas.ActivityFrame)
def read_activityframe(activityframe_id: int, db: Session = Depends(_services.get_db)):
    db_activityframe = _services.get_activityframe(db=db, activityframe_id=activityframe_id)
    if db_activityframe is None:
        raise HTTPException(
            status_code=404, detail="ActivityFrame not found"
        )
    return db_activityframe

# Endpoints for ActivityTarget
@app.post("/activitytargets/", tags=["Activity Target"], response_model=_schemas.ActivityTarget)
def create_activitytarget(
    activitytarget: _schemas.ActivityTargetCreate, db: Session = Depends(_services.get_db)
):
    # Create activity target based on the provided data
    return _services.create_activitytarget(db=db, activitytarget=activitytarget)

@app.get("/activitytargets/", tags=["Activity Target"], response_model=List[_schemas.ActivityTarget])
def read_activitytargets(skip: int = 0, limit: int = 10, db: Session = Depends(_services.get_db)):
    activitytargets = _services.get_activitytargets(db=db, skip=skip, limit=limit)
    return activitytargets

@app.get("/activitytargets/{activitytarget_id}", tags=["Activity Target"], response_model=_schemas.ActivityTarget)
def read_activitytarget(activitytarget_id: int, db: Session = Depends(_services.get_db)):
    db_activitytarget = _services.get_activitytarget(db=db, activitytarget_id=activitytarget_id)
    if db_activitytarget is None:
        raise HTTPException(
            status_code=404, detail="ActivityTarget not found"
        )
    return db_activitytarget

# Endpoints for ActivityType
@app.post("/activitytypes/", tags=["Activity Type"], response_model=_schemas.ActivityType)
def create_activitytype(
    activitytype: _schemas.ActivityTypeCreate, db: Session = Depends(_services.get_db)
):
    # Create activity type based on the provided data
    return _services.create_activitytype(db=db, activitytype=activitytype)

@app.get("/activitytypes/", tags=["Activity Type"], response_model=List[_schemas.ActivityType])
def read_activitytypes(skip: int = 0, limit: int = 10, db: Session = Depends(_services.get_db)):
    activitytypes = _services.get_activitytypes(db=db, skip=skip, limit=limit)
    return activitytypes

@app.get("/activitytypes/{activitytype_id}", tags=["Activity Type"], response_model=_schemas.ActivityType)
def read_activitytype(activitytype_id: int, db: Session = Depends(_services.get_db)):
    db_activitytype = _services.get_activitytype(db=db, activitytype_id=activitytype_id)
    if db_activitytype is None:
        raise HTTPException(
            status_code=404, detail="ActivityType not found"
        )
    return db_activitytype

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
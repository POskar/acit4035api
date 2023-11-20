from sqlalchemy.orm import Session
from . import models, database, schemas


def create_database():
    return database.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_medicalpersonel(db: Session, medicalpersonel_id: int):
    return db.query(models.MedicalPersonel).filter(models.MedicalPersonel.id == medicalpersonel_id).first()

def get_medicalpersonel_by_email(db: Session, email: str):
    return db.query(models.MedicalPersonel).filter(models.MedicalPersonel.email == email).first()

def get_medicalpersonels(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.MedicalPersonel).offset(skip).limit(limit).all()

def create_medicalpersonel(db: Session, medicalpersonel: schemas.MedicalPersonelCreate):
    hashed_password = medicalpersonel.password + "thisisnotsecure"
    db_medicalpersonel = models.MedicalPersonel(
        first_name=medicalpersonel.first_name,
        last_name=medicalpersonel.last_name,
        email=medicalpersonel.email,
        position=medicalpersonel.position, 
        hashed_password=hashed_password
        )
    db.add(db_medicalpersonel)
    db.commit()
    db.refresh(db_medicalpersonel)
    return db_medicalpersonel

def delete_medicalpersonel(db: Session, medicalpersonel_id: int):
    medicalpersonel = db.query(models.MedicalPersonel).filter(models.MedicalPersonel.id == medicalpersonel_id).first()
    db.delete(medicalpersonel)
    db.commit()

def update_medicalpersonel(db: Session, medicalpersonel_id: int, medicalpersonel: schemas.MedicalPersonelCreate):
    db_medicalpersonel = get_medicalpersonel(db=db, medicalpersonel_id=medicalpersonel_id)
    db_medicalpersonel.first_name = medicalpersonel.first_name
    db_medicalpersonel.last_name = medicalpersonel.last_name
    db_medicalpersonel.email = medicalpersonel.email
    db_medicalpersonel.password = medicalpersonel.password
    db_medicalpersonel.position = medicalpersonel.position
    db.commit()
    db.refresh(db_medicalpersonel)
    return db_medicalpersonel


def get_patient(db: Session, patient_id: int):
    return db.query(models.Patient).filter(models.Patient.id == patient_id).first()

def get_patient_by_email(db: Session, email: str):
    return db.query(models.Patient).filter(models.Patient.email == email).first()

def get_patients(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Patient).offset(skip).limit(limit).all()

def create_patient(db: Session, patient: schemas.PatientCreate):
    hashed_password = patient.password + "thisisnotsecure"
    db_patient = models.Patient(
        first_name = patient.first_name,
        last_name = patient.last_name,
        email = patient.email,
        hashed_password=hashed_password,
        medicalpersonel_id=patient.medicalpersonel_id
        )
    db.add(db_patient)
    db.commit()
    db.refresh(db_patient)
    return db_patient

def delete_patient(db: Session, patient_id: int):
    patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
    db.delete(patient)
    db.commit()

def update_patient(db: Session, patient_id: int, patient: schemas.PatientCreate):
    db_patient = get_patient(db=db, patient_id=patient_id)
    db_patient.first_name = patient.first_name
    db_patient.last_name = patient.last_name
    db_patient.email = patient.email
    db_patient.password = patient.password
    db.commit()
    db.refresh(db_patient)
    return db_patient


def get_device(db: Session, device_id: int):
    return db.query(models.Device).filter(models.Device.id == device_id).first()

def get_devices(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.Device).offset(skip).limit(limit).all()

def create_device(db: Session, device: schemas.DeviceCreate):
    db_device = models.Device(mac_address=device.mac_address)
    db.add(db_device)
    db.commit()
    db.refresh(db_device)
    return db_device

def delete_device(db: Session, device_id: int):
    device = db.query(models.Device).filter(models.Device.id == device_id).first()
    db.delete(device)
    db.commit()

def update_device(db: Session, device_id: int, device: schemas.DeviceCreate):
    db_device = get_device(db=db, device_id=device_id)
    db_device.mac_address = device.mac_address
    db.commit()
    db.refresh(db_device)
    return db_device


def get_activityframe(db: Session, activityframe_id: int):
    return db.query(models.ActivityFrame).filter(models.ActivityFrame.id == activityframe_id).first()

def get_activityframes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ActivityFrame).offset(skip).limit(limit).all()

def create_activityframe(db: Session, activityframe: schemas.ActivityFrameCreate):
    db_activityframe = models.ActivityFrame(
        activity_id = activityframe.activity_id,
        time_started = activityframe.time_started,
        time_finished = activityframe.time_finished,
        patient_id = activityframe.patient_id
    )
    db.add(db_activityframe)
    db.commit()
    db.refresh(db_activityframe)
    return db_activityframe

def delete_activityframe(db: Session, activityframe_id: int):
    activityframe = db.query(models.ActivityFrame).filter(models.ActivityFrame.id == activityframe_id).first()
    db.delete(activityframe)
    db.commit()

def update_activityframe(db: Session, activityframe_id: int, activityframe: schemas.ActivityFrameCreate):
    db_activityframe = get_activityframe(db=db, activityframe_id=activityframe_id)
    db_activityframe.activity_id = activityframe.activity_id
    db_activityframe.time_started = activityframe.time_started
    db_activityframe.time_finished = activityframe.time_finished
    db.refresh(db_activityframe)
    return db_activityframe


def get_activitytarget(db: Session, activitytarget_id: int):
    return db.query(models.ActivityTarget).filter(models.ActivityTarget.id == activitytarget_id).first()

def get_activitytargets(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ActivityTarget).offset(skip).limit(limit).all()

def create_activitytarget(db: Session, activitytarget: schemas.ActivityTargetCreate):
    db_activitytarget = models.ActivityTarget(
        medicalpersonel_id = activitytarget.medicalpersonel_id,
        activity_id = activitytarget.activity_id,
        date = activitytarget.date
    )
    db.add(db_activitytarget)
    db.commit()
    db.refresh(db_activitytarget)
    return db_activitytarget

def delete_activitytarget(db: Session, activitytarget_id: int):
    activitytarget = db.query(models.ActivityTarget).filter(models.ActivityTarget.id == activitytarget_id).first()
    db.delete(activitytarget)
    db.commit()

def update_activitytarget(db: Session, activitytarget_id: int, activitytarget: schemas.ActivityTargetCreate):
    db_activitytarget = get_activitytarget(db=db, activitytarget_id=activitytarget_id)
    db_activitytarget.medicalpersonel_id = activitytarget.medicalpersonel_id
    db_activitytarget.activity_id = activitytarget.activity_id
    db_activitytarget.date = activitytarget.date
    db.commit()
    db.refresh(db_activitytarget)
    return db_activitytarget


def get_activitytype(db: Session, activitytype_id: int):
    return db.query(models.ActivityType).filter(models.ActivityType.id == activitytype_id).first()

def get_activitytypes(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.ActivityType).offset(skip).limit(limit).all()

def create_activitytype(db: Session, activitytype: schemas.ActivityTypeCreate):
    db_activitytype = models.ActivityType(type = activitytype.type)
    db.add(db_activitytype)
    db.commit()
    db.refresh(db_activitytype)
    return db_activitytype

def delete_activitytype(db: Session, activitytype_id: int):
    activitytype = db.query(models.ActivityType).filter(models.ActivityType.id == activitytype_id).first()
    db.delete(activitytype)
    db.commit()

def update_activitytype(db: Session, activitytype_id: int, activitytype: schemas.ActivityTypeCreate):
    db_activitytype = get_activitytype(db=db, activitytype_id=activitytype_id)
    db_activitytype.type = activitytype.type
    db.commit()
    db.refresh(db_activitytype)
    return db_activitytype
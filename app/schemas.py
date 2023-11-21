from pydantic import BaseModel
from typing import List
from datetime import datetime

# Medical Personel
class _MedicalPersonelBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    position: str

class MedicalPersonelCreate(_MedicalPersonelBase):
    password: str

class MedicalPersonel(_MedicalPersonelBase):
    id: int
    date_created: datetime

    class Config:
        orm_mode = True

# Patient
class _PatientBase(BaseModel):
    first_name: str
    last_name: str
    email: str

class PatientCreate(_PatientBase):
    password: str
    medicalpersonel_id: int

class Patient(_PatientBase):
    id: int
    date_created: datetime
    medicalpersonel_id: int

    class Config:
        orm_mode = True

# Device
class _DeviceBase(BaseModel):
    mac_address: str

class DeviceCreate(_DeviceBase):
    pass

class Device(_DeviceBase):
    id: int
    date_created: datetime
    patient_id: int

    class Config:
        orm_mode = True

# ActivityFrame
class _ActivityFrameBase(BaseModel):
    patient_id: int
    activity_id: int
    date_started: datetime
    date_finished: datetime

class ActivityFrameCreate(_ActivityFrameBase):
    pass

class ActivityFrame(_ActivityFrameBase):
    id: int

    class Config:
        orm_mode = True


# ActivityTarget
class _ActivityTargetBase(BaseModel):
    patient_id: int
    activity_id: int
    medicalpersonel_id: int

class ActivityTargetCreate(_ActivityTargetBase):
    pass

class ActivityTarget(_ActivityTargetBase):
    id: int
    date: datetime

    class Config:
        orm_mode = True


# ActivityType
class _ActivityTypeBase(BaseModel):
    type: str

class ActivityTypeCreate(_ActivityTypeBase):
    pass

class ActivityType(_ActivityTypeBase):
    id: int

    class Config:
        orm_mode = True

# Custom schemas for endpoints
class ActivityFrameRequest(BaseModel):
    currentTime: datetime
    deviceTime: int
    dataFromDevice: str
    patientId: int
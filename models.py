import datetime as _dt
import sqlalchemy as _sql
import sqlalchemy.orm as _orm

import app.database as _database


class MedicalPersonel(_database.Base):
    __tablename__ = "medicalpersonel"
    id = _sql.Column(_sql.Integer, primary_key=True)
    first_name = _sql.Column(_sql.String)
    last_name = _sql.Column(_sql.String)
    email = _sql.Column(_sql.String, unique=True)
    hashed_password = _sql.Column(_sql.String)
    position = _sql.Column(_sql.String)
    date_created = _sql.Column(_sql.DateTime, default=_dt.datetime.utcnow)

    patients = _orm.relationship("Patient", back_populates="medicalpersonel")
    activityTargets = _orm.relationship("ActivityTarget", back_populates="medicalpersonel")


class Patient(_database.Base):
    __tablename__ = "patients"
    id = _sql.Column(_sql.Integer, primary_key=True)
    first_name = _sql.Column(_sql.String)
    last_name = _sql.Column(_sql.String)
    email = _sql.Column(_sql.String, unique=True)
    hashed_password = _sql.Column(_sql.String)
    date_created = _sql.Column(_sql.DateTime, default=_dt.datetime.utcnow)
    medicalpersonel_id = _sql.Column(_sql.Integer, _sql.ForeignKey("medicalpersonel.id"))

    medicalpersonel = _orm.relationship("MedicalPersonel", back_populates="patients")
    device = _orm.relationship("Device", back_populates="patient", uselist=False)
    activityFrames = _orm.relationship("ActivityFrame", back_populates="patient")
    activityTargets = _orm.relationship("ActivityTarget", back_populates="patient")


class Device(_database.Base):
    __tablename__ = "devices"
    id = _sql.Column(_sql.Integer, primary_key=True)
    mac_address = _sql.Column(_sql.String, unique=True)
    date_created = _sql.Column(_sql.DateTime, default=_dt.datetime.utcnow)
    patient_id = _sql.Column(_sql.Integer, _sql.ForeignKey("patients.id"))

    patient = _orm.relationship("Patient", back_populates="device")


class ActivityFrame(_database.Base):
    __tablename__ = "activityFrames"
    id = _sql.Column(_sql.Integer, primary_key=True)
    patient_id = _sql.Column(_sql.Integer, _sql.ForeignKey("patients.id"))
    activity_id = _sql.Column(_sql.Integer, _sql.ForeignKey("activitytypes.id"))
    time_started = _sql.Column(_sql.BigInteger)
    time_finished = _sql.Column(_sql.BigInteger)

    patient = _orm.relationship("Patient", back_populates="activityFrames")
    activity_type = _orm.relationship("ActivityType", back_populates="frame")


class ActivityTarget(_database.Base):
    __tablename__ = "activityTargets"
    id = _sql.Column(_sql.Integer, primary_key=True)
    patient_id = _sql.Column(_sql.Integer, _sql.ForeignKey("patients.id"))
    activity_id = _sql.Column(_sql.Integer, _sql.ForeignKey("activitytypes.id"))
    medicalpersonel_id = _sql.Column(_sql.Integer, _sql.ForeignKey("medicalpersonel.id"))
    date = _sql.Column(_sql.DateTime, default=_dt.datetime.utcnow)

    medicalpersonel = _orm.relationship("MedicalPersonel", back_populates="activityTargets")
    activity_type = _orm.relationship("ActivityType", back_populates="target")
    patient = _orm.relationship("Patient", back_populates="activityTargets")


class ActivityType(_database.Base):
    __tablename__ = "activitytypes"
    id = _sql.Column(_sql.Integer, primary_key=True)
    type = _sql.Column(_sql.String, unique=True)

    frame = _orm.relationship("ActivityFrame", back_populates="activity_type")
    target = _orm.relationship("ActivityTarget", back_populates="activity_type")
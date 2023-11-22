from fastapi import Path, Query, FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, time, timedelta, timezone

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

    deviceEnabledTime = requestData.currentTime - timedelta(milliseconds=requestData.deviceTime)

    # Split the data from the device, and group the values into sets of (activity_id, time_started, time_finished)
    values = requestData.dataFromDevice.split(";")

    # Clean the data by removing anything that isn't a number or ;
    cleaned_values = [value for value in values if value.isdigit() or value == ";"]

    # Group the cleaned values
    grouped_values = [cleaned_values[i:i + 3] for i in range(0, len(cleaned_values), 3) if len(cleaned_values[i:i + 3]) == 3]

    # Filter out groups that don't start with a single digit
    grouped_values = [group for group in grouped_values if group[0].isdigit() and len(group[0]) == 1]

    # Iterate through each group of values
    for group in grouped_values:
        # Calculate time_started and time_finished based on device_enabled_time and values in group[1] and group[2]
        date_started = deviceEnabledTime + timedelta(milliseconds=int(group[1]))
        date_finished = deviceEnabledTime + timedelta(milliseconds=int(group[2]))

        # Check if date_started is greater than date_finished
        if date_started > date_finished:
            # Skip this record and move to the next one
            continue

        # Create a dictionary with data for a single activity frame
        activityFrameData = {
            "patient_id": requestData.patientId,
            "activity_id": group[0],
            "date_started": date_started,
            "date_finished": date_finished
        }

        # Create an ActivityFrameCreate instance from the dictionary
        activityframe = _schemas.ActivityFrameCreate(**activityFrameData)

        # Call the service function to create the activity frame in the database
        created_frame = _services.create_activityframe(db=db, activityframe=activityframe)
        created_activityframes.append(created_frame)

    return created_activityframes

@app.get("/activityframes/{patient_id}/date/{activity_date}", tags=["Active Testing"], response_model=List[_schemas.ActivityFrame])
def get_activityframes_for_date(patient_id: int, activity_date: datetime, db: Session = Depends(_services.get_db)):
    # Assuming you store both `date_started` and `date_finished` in UTC
    start_datetime = datetime.combine(activity_date, time.min).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(activity_date, time.max).replace(tzinfo=timezone.utc)

    activityframes = _services.get_activityframes_for_patient_and_date(db=db, patient_id=patient_id, start_datetime=start_datetime, end_datetime=end_datetime)
    return activityframes

@app.get("/daily-summary/{patient_id}/date/{activity_date}", tags=["Active Testing"], response_model=_schemas.DailySummary)
def get_daily_summary(patient_id: int, activity_date: datetime, db: Session = Depends(_services.get_db)):
    # Get all activity frames for the specified patient and date
    start_datetime = datetime.combine(activity_date, time.min).replace(tzinfo=timezone.utc)
    end_datetime = datetime.combine(activity_date, time.max).replace(tzinfo=timezone.utc)
    activityframes = _services.get_activityframes_for_patient_and_date(db=db, patient_id=patient_id, start_datetime=start_datetime, end_datetime=end_datetime)

    # Initialize variables to store the duration of each activity
    time_on_random = 0
    time_on_clapping = 0
    time_on_brushing_teeth = 0
    time_on_washing_hands = 0
    time_on_combing_hair = 0

    # Iterate through each activity frame and calculate the duration for each activity
    for activityframe in activityframes:
        activity_id = activityframe.activity_id
        duration = (activityframe.date_finished - activityframe.date_started).total_seconds()

        if activity_id == 0:
            time_on_random += duration
        elif activity_id == 1:
            time_on_clapping += duration
        elif activity_id == 2:
            time_on_brushing_teeth += duration
        elif activity_id == 3:
            time_on_washing_hands += duration
        elif activity_id == 4:
            time_on_combing_hair += duration

    # Create and return the Summary instance
    summary = _schemas.DailySummary(
        date=activity_date.strftime("%Y-%m-%d"),
        motion=_schemas.ActivityDuration(
            activityDurationInSeconds=int(time_on_clapping) + int(time_on_brushing_teeth) + int(time_on_combing_hair) + int(time_on_washing_hands) + int(time_on_random),
            #  TODO: change 600
            activityTargetInSeconds=600
        ),
        clapping=_schemas.ActivityDuration(
            activityDurationInSeconds=int(time_on_clapping),
            activityTargetInSeconds=None
        ),
        brushingTeeth=_schemas.ActivityDuration(
            activityDurationInSeconds=int(time_on_brushing_teeth),
            activityTargetInSeconds=None
        ),
        brushingHair=_schemas.ActivityDuration(
            activityDurationInSeconds=int(time_on_combing_hair),
            activityTargetInSeconds=None
        ),
        cleaningHands=_schemas.ActivityDuration(
            activityDurationInSeconds=int(time_on_washing_hands),
            activityTargetInSeconds=None
        ),
        randomMotion=_schemas.ActivityDuration(
            activityDurationInSeconds=int(time_on_random),
            activityTargetInSeconds=None
        ),
    )

    return summary

@app.get("/monthly-summary/{patient_id}/month/{activity_month}", tags=["Active Testing"], response_model=_schemas.MonthlySummary)
def get_monthly_summary(patient_id: int, activity_month: datetime, db: Session = Depends(_services.get_db)):
    # Calculate the start_date (first day of the month) and end_date (last day of the month)
    start_date = datetime.combine(activity_month.replace(day=1), time.min).replace(tzinfo=timezone.utc)
    next_month = (activity_month.replace(day=28) + timedelta(days=4)).replace(day=1)
    end_date = (next_month - timedelta(days=1)).replace(hour=23, minute=59, second=59).replace(tzinfo=timezone.utc)

    # Get all activity frames for the specified patient and date range
    activityframes = _services.get_activityframes_for_patient_and_date(db=db, patient_id=patient_id, start_datetime=start_date, end_datetime=end_date)

    # Initialize a list to store daily summaries
    monthly_summaries = []

    # Iterate through each day in the month and create a daily summary
    current_date = start_date
    while current_date <= end_date:
        # Initialize variables to store the duration of each activity for the current day
        time_on_random = 0
        time_on_clapping = 0
        time_on_brushing_teeth = 0
        time_on_washing_hands = 0
        time_on_combing_hair = 0

        # Iterate through each activity frame for the current day and calculate the duration for each activity
        for activityframe in activityframes:
            if current_date.date() == activityframe.date_started.date():
                activity_id = activityframe.activity_id
                duration = (activityframe.date_finished - activityframe.date_started).total_seconds()

                if activity_id == 0:
                    time_on_random += duration
                elif activity_id == 1:
                    time_on_clapping += duration
                elif activity_id == 2:
                    time_on_brushing_teeth += duration
                elif activity_id == 3:
                    time_on_washing_hands += duration
                elif activity_id == 4:
                    time_on_combing_hair += duration

        # Create and append the daily summary
        daily_summary = _schemas.DailySummary(
            date=current_date.strftime("%Y-%m-%d"),
            motion=_schemas.ActivityDuration(
                activityDurationInSeconds=int(time_on_clapping) + int(time_on_brushing_teeth) + int(
                    time_on_combing_hair) + int(time_on_washing_hands) + int(time_on_random),
                #  TODO: change 600
                activityTargetInSeconds=600
            ),
            clapping=_schemas.ActivityDuration(
                activityDurationInSeconds=int(time_on_clapping),
                activityTargetInSeconds=None
            ),
            brushingTeeth=_schemas.ActivityDuration(
                activityDurationInSeconds=int(time_on_brushing_teeth),
                activityTargetInSeconds=None
            ),
            brushingHair=_schemas.ActivityDuration(
                activityDurationInSeconds=int(time_on_combing_hair),
                activityTargetInSeconds=None
            ),
            cleaningHands=_schemas.ActivityDuration(
                activityDurationInSeconds=int(time_on_washing_hands),
                activityTargetInSeconds=None
            ),
            randomMotion=_schemas.ActivityDuration(
                activityDurationInSeconds=int(time_on_random),
                activityTargetInSeconds=None
            ),
        )
        monthly_summaries.append(daily_summary)

        # Move to the next day
        current_date += timedelta(days=1)

    # Create and return the MonthlySummary instance
    monthly_summary = _schemas.MonthlySummary(monthlySummaries=monthly_summaries)

    return monthly_summary

@app.get("/monthly_summaries/", tags=["Active Testing"], response_model=_schemas.MonthlySummary)
def get_monthly_summaries(patient_id: int, activity_month: datetime, db: Session = Depends(_services.get_db)):
    # Replace the provided JSON with your actual data
    data_by_month = {
    "2023-09": [{"date":"2023-09-01","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":580,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":70,"activityTargetInSeconds":120},"cleaningHands":{"activityDurationInSeconds":110,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2920,"activityTargetInSeconds":None}},{"date":"2023-09-02","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":660,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":420,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":320,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":270,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2330,"activityTargetInSeconds":None}},{"date":"2023-09-03","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":500,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":0,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":120},"cleaningHands":{"activityDurationInSeconds":140,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2920,"activityTargetInSeconds":None}},{"date":"2023-09-04","motion":{"activityDurationInSeconds":4300,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3440,"activityTargetInSeconds":None}},{"date":"2023-09-05","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":540,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":200,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3370,"activityTargetInSeconds":None}},{"date":"2023-09-06","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3520,"activityTargetInSeconds":None}},{"date":"2023-09-07","motion":{"activityDurationInSeconds":3700,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":640,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2440,"activityTargetInSeconds":None}},{"date":"2023-09-08","motion":{"activityDurationInSeconds":4900,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":720,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":170,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":250,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3540,"activityTargetInSeconds":None}},{"date":"2023-09-09","motion":{"activityDurationInSeconds":5400,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":620,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":130,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":270,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-09-10","motion":{"activityDurationInSeconds":5000,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3840,"activityTargetInSeconds":None}},{"date":"2023-09-11","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":560,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3300,"activityTargetInSeconds":None}},{"date":"2023-09-12","motion":{"activityDurationInSeconds":5000,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":230,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3710,"activityTargetInSeconds":None}},{"date":"2023-09-13","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":640,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":190,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2850,"activityTargetInSeconds":None}},{"date":"2023-09-14","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3140,"activityTargetInSeconds":None}},{"date":"2023-09-15","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":720,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":190,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2810,"activityTargetInSeconds":None}},{"date":"2023-09-16","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":250,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2800,"activityTargetInSeconds":None}},{"date":"2023-09-17","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":700,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":200,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2800,"activityTargetInSeconds":None}},{"date":"2023-09-18","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":820,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":300,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2600,"activityTargetInSeconds":None}},{"date":"2023-09-19","motion":{"activityDurationInSeconds":4300,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3450,"activityTargetInSeconds":None}},{"date":"2023-09-20","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":3600},"clapping":{"activityDurationInSeconds":660,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":170,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3030,"activityTargetInSeconds":None}},{"date":"2023-09-21","motion":{"activityDurationInSeconds":3600,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":760,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2360,"activityTargetInSeconds":None}},{"date":"2023-09-22","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":980,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2240,"activityTargetInSeconds":None}},{"date":"2023-09-23","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":920,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":140,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2500,"activityTargetInSeconds":None}},{"date":"2023-09-24","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":940,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":140,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2460,"activityTargetInSeconds":None}},{"date":"2023-09-25","motion":{"activityDurationInSeconds":5200,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":820,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":0,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3980,"activityTargetInSeconds":None}},{"date":"2023-09-26","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-09-27","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-09-28","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-09-29","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-09-30","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":300},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}}],
    "2023-10": [{"date":"2023-10-01","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":580,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":70,"activityTargetInSeconds":120},"cleaningHands":{"activityDurationInSeconds":110,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2920,"activityTargetInSeconds":None}},{"date":"2023-10-02","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":660,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":420,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":320,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":270,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2330,"activityTargetInSeconds":None}},{"date":"2023-10-03","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":500,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":0,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":120},"cleaningHands":{"activityDurationInSeconds":140,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2920,"activityTargetInSeconds":None}},{"date":"2023-10-04","motion":{"activityDurationInSeconds":4300,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3440,"activityTargetInSeconds":None}},{"date":"2023-10-05","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":540,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":200,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3370,"activityTargetInSeconds":None}},{"date":"2023-10-06","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3520,"activityTargetInSeconds":None}},{"date":"2023-10-07","motion":{"activityDurationInSeconds":3700,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":640,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2440,"activityTargetInSeconds":None}},{"date":"2023-10-08","motion":{"activityDurationInSeconds":4900,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":720,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":170,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":250,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3540,"activityTargetInSeconds":None}},{"date":"2023-10-09","motion":{"activityDurationInSeconds":5400,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":620,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":130,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":270,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-10-10","motion":{"activityDurationInSeconds":5000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3840,"activityTargetInSeconds":None}},{"date":"2023-10-11","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":560,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3300,"activityTargetInSeconds":None}},{"date":"2023-10-12","motion":{"activityDurationInSeconds":5000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":230,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3710,"activityTargetInSeconds":None}},{"date":"2023-10-13","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":640,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":190,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2850,"activityTargetInSeconds":None}},{"date":"2023-10-14","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3140,"activityTargetInSeconds":None}},{"date":"2023-10-15","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":720,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":190,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2810,"activityTargetInSeconds":None}},{"date":"2023-10-16","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":250,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2800,"activityTargetInSeconds":None}},{"date":"2023-10-17","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":700,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":200,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2800,"activityTargetInSeconds":None}},{"date":"2023-10-18","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":820,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":300,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2600,"activityTargetInSeconds":None}},{"date":"2023-10-19","motion":{"activityDurationInSeconds":4300,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3450,"activityTargetInSeconds":None}},{"date":"2023-10-20","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":660,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":170,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3030,"activityTargetInSeconds":None}},{"date":"2023-10-21","motion":{"activityDurationInSeconds":3600,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":760,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2360,"activityTargetInSeconds":None}},{"date":"2023-10-22","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":980,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2240,"activityTargetInSeconds":None}},{"date":"2023-10-23","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":920,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":140,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2500,"activityTargetInSeconds":None}},{"date":"2023-10-24","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":940,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":140,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2460,"activityTargetInSeconds":None}},{"date":"2023-10-25","motion":{"activityDurationInSeconds":5200,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":820,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":0,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3980,"activityTargetInSeconds":None}},{"date":"2023-10-26","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-10-27","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-10-28","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-10-29","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-10-30","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-10-31","motion":{"activityDurationInSeconds":5600,"activityTargetInSeconds":4800},"clapping":{"activityDurationInSeconds":960,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":80,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}}],
    "2023-11": [{"date":"2023-11-01","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":580,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":70,"activityTargetInSeconds":120},"cleaningHands":{"activityDurationInSeconds":110,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2920,"activityTargetInSeconds":None}},{"date":"2023-11-02","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":660,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":420,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":320,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":270,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2330,"activityTargetInSeconds":None}},{"date":"2023-11-03","motion":{"activityDurationInSeconds":3800,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":500,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":0,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":120},"cleaningHands":{"activityDurationInSeconds":140,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2920,"activityTargetInSeconds":None}},{"date":"2023-11-04","motion":{"activityDurationInSeconds":4300,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3440,"activityTargetInSeconds":None}},{"date":"2023-11-05","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":540,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":200,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3370,"activityTargetInSeconds":None}},{"date":"2023-11-06","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3520,"activityTargetInSeconds":None}},{"date":"2023-11-07","motion":{"activityDurationInSeconds":3700,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":640,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2440,"activityTargetInSeconds":None}},{"date":"2023-11-08","motion":{"activityDurationInSeconds":4900,"activityTargetInSeconds":4200},"clapping":{"activityDurationInSeconds":720,"activityTargetInSeconds":600},"brushingTeeth":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":170,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":250,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3540,"activityTargetInSeconds":None}},{"date":"2023-11-09","motion":{"activityDurationInSeconds":5400,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":620,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":130,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":270,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":None}},{"date":"2023-11-10","motion":{"activityDurationInSeconds":5000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3840,"activityTargetInSeconds":None}},{"date":"2023-11-11","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":560,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3300,"activityTargetInSeconds":None}},{"date":"2023-11-12","motion":{"activityDurationInSeconds":5000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":230,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3710,"activityTargetInSeconds":None}},{"date":"2023-11-13","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":640,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":190,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2850,"activityTargetInSeconds":None}},{"date":"2023-11-14","motion":{"activityDurationInSeconds":4500,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":220,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":160,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3140,"activityTargetInSeconds":None}},{"date":"2023-11-15","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":720,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":190,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2810,"activityTargetInSeconds":None}},{"date":"2023-11-16","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":740,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":250,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2800,"activityTargetInSeconds":None}},{"date":"2023-11-17","motion":{"activityDurationInSeconds":4000,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":700,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":200,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2800,"activityTargetInSeconds":None}},{"date":"2023-11-18","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":820,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":300,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":2600,"activityTargetInSeconds":None}},{"date":"2023-11-19","motion":{"activityDurationInSeconds":4300,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":460,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":60,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":150,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3450,"activityTargetInSeconds":None}},{"date":"2023-11-20","motion":{"activityDurationInSeconds":4200,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":660,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":100,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":240,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":170,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3030,"activityTargetInSeconds":None}},{"date":"2023-11-20","motion":{"activityDurationInSeconds":4800,"activityTargetInSeconds":4500},"clapping":{"activityDurationInSeconds":660,"activityTargetInSeconds":900},"brushingTeeth":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"brushingHair":{"activityDurationInSeconds":120,"activityTargetInSeconds":None},"cleaningHands":{"activityDurationInSeconds":180,"activityTargetInSeconds":None},"randomMotion":{"activityDurationInSeconds":3030,"activityTargetInSeconds":None}}]
    }

    month_key = activity_month.strftime("%Y-%m")
    if month_key in data_by_month:
        monthly_summaries = data_by_month[month_key]
        if month_key == "2023-11":
            activity_date = datetime.fromisoformat('2023-11-22T00:05:23')
            # Get all activity frames for the specified patient and date
            start_datetime = datetime.combine(activity_date, time.min).replace(tzinfo=timezone.utc)
            end_datetime = datetime.combine(activity_date, time.max).replace(tzinfo=timezone.utc)
            activityframes = _services.get_activityframes_for_patient_and_date(db=db, patient_id=patient_id, start_datetime=start_datetime, end_datetime=end_datetime)

            # Initialize variables to store the duration of each activity
            time_on_random = 0
            time_on_clapping = 0
            time_on_brushing_teeth = 0
            time_on_washing_hands = 0
            time_on_combing_hair = 0

            # Iterate through each activity frame and calculate the duration for each activity
            for activityframe in activityframes:
                activity_id = activityframe.activity_id
                duration = (activityframe.date_finished - activityframe.date_started).total_seconds()

                if activity_id == 0:
                    time_on_random += duration
                elif activity_id == 1:
                    time_on_clapping += duration
                elif activity_id == 2:
                    time_on_brushing_teeth += duration
                elif activity_id == 3:
                    time_on_washing_hands += duration
                elif activity_id == 4:
                    time_on_combing_hair += duration

            monthly_summaries.append({
            "date": activity_date.strftime("%Y-%m-%d"),
            "motion": {
                "activityDurationInSeconds": int(time_on_clapping) + int(time_on_brushing_teeth) + int(
                    time_on_combing_hair) + int(time_on_washing_hands) + int(time_on_random),
                "activityTargetInSeconds": 600
            },
            "clapping": {
                "activityDurationInSeconds": int(time_on_clapping),
                "activityTargetInSeconds": None
            },
            "brushingTeeth": {
                "activityDurationInSeconds": int(time_on_brushing_teeth),
                "activityTargetInSeconds": None
            },
            "brushingHair": {
                "activityDurationInSeconds": int(time_on_combing_hair),
                "activityTargetInSeconds": None
            },
            "cleaningHands": {
                "activityDurationInSeconds": int(time_on_washing_hands),
                "activityTargetInSeconds": None
            },
            "randomMotion": {
                "activityDurationInSeconds": int(time_on_random),
                "activityTargetInSeconds": None
            },
        })
    else:
        # Use a default value if the month is not found
        monthly_summaries = data_by_month["2023-09"]

    # Convert the JSON data to MonthlySummary objects
    monthly_summary = _schemas.MonthlySummary(
    monthlySummaries=[
        _schemas.DailySummary(
            **summary
        ) for summary in monthly_summaries
    ]
)

    return monthly_summary

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
"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse
import os
from pathlib import Path
import sqlite3
from typing import Dict, Any, List

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# Seed activities used to initialize the database if empty
seed_activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"]
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"]
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"]
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"]
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"]
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"]
    }
}

# SQLite database file
DB_PATH = Path(__file__).parent / "activities.db"


def _connect():
    return sqlite3.connect(str(DB_PATH))


def init_db():
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS activities (
                name TEXT PRIMARY KEY,
                description TEXT,
                schedule TEXT,
                max_participants INTEGER
            )
            """
        )
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS participants (
                activity_name TEXT,
                email TEXT,
                PRIMARY KEY(activity_name, email),
                FOREIGN KEY(activity_name) REFERENCES activities(name) ON DELETE CASCADE
            )
            """
        )
        conn.commit()

        # Seed activities if table empty
        cur.execute("SELECT COUNT(*) FROM activities")
        count = cur.fetchone()[0]
        if count == 0:
            for name, details in seed_activities.items():
                cur.execute(
                    "INSERT INTO activities (name, description, schedule, max_participants) VALUES (?, ?, ?, ?)",
                    (name, details["description"], details["schedule"], details["max_participants"]),
                )
                for email in details.get("participants", []):
                    cur.execute(
                        "INSERT INTO participants (activity_name, email) VALUES (?, ?)", (name, email)
                    )
            conn.commit()
    finally:
        conn.close()


def get_activities_from_db() -> Dict[str, Any]:
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT name, description, schedule, max_participants FROM activities")
        rows = cur.fetchall()
        result: Dict[str, Any] = {}
        for name, description, schedule, max_participants in rows:
            cur.execute("SELECT email FROM participants WHERE activity_name = ?", (name,))
            participants = [r[0] for r in cur.fetchall()]
            result[name] = {
                "description": description,
                "schedule": schedule,
                "max_participants": max_participants,
                "participants": participants,
            }
        return result
    finally:
        conn.close()


def add_participant(activity_name: str, email: str):
    conn = _connect()
    try:
        cur = conn.cursor()
        # check activity exists
        cur.execute("SELECT max_participants FROM activities WHERE name = ?", (activity_name,))
        row = cur.fetchone()
        if row is None:
            raise KeyError("Activity not found")
        max_participants = row[0]
        cur.execute("SELECT COUNT(*) FROM participants WHERE activity_name = ?", (activity_name,))
        count = cur.fetchone()[0]
        if count >= max_participants:
            raise ValueError("Activity is full")
        # check already registered
        cur.execute("SELECT 1 FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
        if cur.fetchone():
            raise FileExistsError("Already registered")
        cur.execute("INSERT INTO participants (activity_name, email) VALUES (?, ?)", (activity_name, email))
        conn.commit()
    finally:
        conn.close()


def remove_participant(activity_name: str, email: str):
    conn = _connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
        if not cur.fetchone():
            raise KeyError("Not registered")
        cur.execute("DELETE FROM participants WHERE activity_name = ? AND email = ?", (activity_name, email))
        conn.commit()
    finally:
        conn.close()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.on_event("startup")
def startup_event():
    init_db()


@app.get("/activities")
def get_activities():
    return get_activities_from_db()


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    try:
        add_participant(activity_name, email)
        return {"message": f"Signed up {email} for {activity_name}"}
    except KeyError:
        raise HTTPException(status_code=404, detail="Activity not found")
    except FileExistsError:
        raise HTTPException(status_code=400, detail="Student is already signed up")
    except ValueError:
        raise HTTPException(status_code=400, detail="Activity is full")


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    try:
        remove_participant(activity_name, email)
        return {"message": f"Unregistered {email} from {activity_name}"}
    except KeyError:
        # Could be activity missing or not registered
        # Check if activity exists to give proper error
        conn = _connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM activities WHERE name = ?", (activity_name,))
            if not cur.fetchone():
                raise HTTPException(status_code=404, detail="Activity not found")
            else:
                raise HTTPException(status_code=400, detail="Student is not signed up for this activity")
        finally:
            conn.close()

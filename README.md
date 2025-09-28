# 🅿️ Python Parking API

A simple parking spot management system built with **FastAPI**, **PostgreSQL (Docker)**, and a lightweight **HTML+JS frontend**.  
This project demonstrates how to design RESTful APIs, manage relational databases, and build a simple UI for end users.

---

## 📌 Features

- ✅ Create and list parking **lots** (with name + GPS coordinates).  
- ✅ Create and list parking **spots** (car, bike, EV) inside lots.  
- ✅ Search for **available spots** nearby using latitude/longitude.  
- ✅ Make and end **reservations** for spots.  
- ✅ Automatic API documentation with **Swagger** (`/docs`).  
- ✅ Minimal HTML frontend for user-friendly testing without Postman.  

---

## 🏗️ Tech Stack

- **Backend:** Python 3.9+, FastAPI, SQLAlchemy ORM  
- **Database:** PostgreSQL 16 (running in Docker)  
- **Frontend:** Plain HTML, CSS, JavaScript (Fetch API)  
- **Server:** Uvicorn (ASGI)  

---

## 🚀 Getting Started

### 1. Clone Repository
```bash
git clone https://github.com/your-username/python-parking-api.git
cd python-parking-api
````

### 2. Run PostgreSQL in Docker

```bash
docker run --name parkingdb ^
  -e POSTGRES_PASSWORD=postgres ^
  -e POSTGRES_DB=parking ^
  -p 5432:5432 -d postgres:16
```

This creates a Postgres database called **parking** with user **postgres** and password **postgres**.

---

### 3. Setup Python Virtual Environment

```bash
python -m venv venv
.\venv\Scripts\activate   # Windows
# source venv/bin/activate  # Linux/Mac
```

### 4. Install Requirements

```bash
pip install -r requirements.txt
```

`requirements.txt`

```
fastapi
uvicorn
sqlalchemy
psycopg2-binary
```

---

### 5. Run FastAPI Server

Set the environment variable for database connection:

```powershell
$env:DATABASE_URL = "postgresql+psycopg2://postgres:postgres@127.0.0.1:5432/parking"
uvicorn main:app --reload
```

The API will be available at:

* Swagger UI → [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
* Health check → [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## 🖥️ Frontend (Demo UI)

A demo UI is included as `index.html`.

### Run it locally:

```bash
python -m http.server 5500
```

Then open: [http://127.0.0.1:5500/index.html](http://127.0.0.1:5500/index.html)

### UI Sections

* **Lots** → Create/List parking lots.
* **Spots** → Create/List parking spots under a lot.
* **Search Nearby** → Search available spots near given coordinates.
* **Reservations** → Reserve a spot and later end the reservation.

---

## 📊 Database Schema

```sql
parking_lot (
  id SERIAL PRIMARY KEY,
  name TEXT,
  latitude DOUBLE PRECISION,
  longitude DOUBLE PRECISION
);

parking_spot (
  id SERIAL PRIMARY KEY,
  lot_id INT REFERENCES parking_lot(id) ON DELETE CASCADE,
  number TEXT,
  type TEXT CHECK (type IN ('car','bike','ev')),
  is_available BOOLEAN DEFAULT TRUE
);

reservation (
  id SERIAL PRIMARY KEY,
  spot_id INT REFERENCES parking_spot(id) ON DELETE CASCADE,
  start_time TIMESTAMPTZ,
  end_time TIMESTAMPTZ,
  vehicle_plate TEXT,
  status TEXT CHECK (status IN ('active','ended','cancelled')) DEFAULT 'active'
);
```

---

## ✅ Example Flow

1. **Create Lot**

   ```json
   {
     "name": "Mall Basement",
     "latitude": 28.6139,
     "longitude": 77.2090
   }
   ```

2. **Create Spot**

   ```json
   {
     "number": "B1-042",
     "type": "car"
   }
   ```

3. **Search Nearby**

   ```
   GET /spots/search?lat=28.6129&lng=77.2295&radius_m=1500
   ```

4. **Create Reservation**

   ```json
   {
     "spot_id": 1,
     "start_time": "2025-09-29T12:00:00Z",
     "end_time": "2025-09-29T14:00:00Z",
     "vehicle_plate": "DL8CAF1234"
   }
   ```

5. **End Reservation**

   ```
   POST /reservations/1/end
   ```

---

## 🎯 Why This Project?

This project is designed as a **learning project** to understand:

* How to build REST APIs with FastAPI.
* How to use PostgreSQL with SQLAlchemy ORM.
* How to containerize services using Docker.
* How to connect frontend + backend using Fetch API.

---

## 📂 Project Structure

```
par/
 ├── main.py          # FastAPI app (all routes + DB models)
 ├── venv/            # Virtual environment
 └── index.html       # Simple frontend UI
```

---

## 📜 License

MIT License © 2025 Prateek Verma
ant me to also include a **`docker-compose.yml`** so you can start both the backend + database + frontend in one command (`docker compose up`)?
```

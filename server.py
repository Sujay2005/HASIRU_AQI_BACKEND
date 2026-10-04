from flask import Flask, request, jsonify
import sqlite3
from datetime import datetime, timezone, timedelta

app = Flask(__name__)

DB = "iot_data.db"
API_KEY = "mysecret123"

# ================= IST TIME FUNCTION =================
def get_ist_time():
    ist = timezone(timedelta(hours=5, minutes=30))
    return datetime.now(ist).strftime("%Y-%m-%d %H:%M:%S")

# ================= INIT DB =================
def init_db():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sensor_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            pm1 REAL,
            pm25 REAL,
            pm10 REAL,
            aqi_raw REAL,
            aqi_calibrated REAL,
            temperature REAL,
            humidity REAL,
            latitude REAL,
            longitude REAL,
            timestamp TEXT
        )
    """)

    conn.commit()
    conn.close()

init_db()

# ================= INSERT =================
def insert_data(data):
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    timestamp = data.get("timestamp")

    # If ESP32 didn't send timestamp → use server IST
    if not timestamp or timestamp == "unknown":
        timestamp = get_ist_time()

    cursor.execute("""
        INSERT INTO sensor_data (
            device_id, pm1, pm25, pm10,
            aqi_raw, aqi_calibrated,
            temperature, humidity,
            latitude, longitude,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get("device_id", "unknown"),
        data.get("pm1", 0),
        data.get("pm25", 0),
        data.get("pm10", 0),
        data.get("aqi", 0),
	data.get("aqi", 0),
        data.get("temperature", 0),
        data.get("humidity", 0),
        data.get("latitude", 0),
        data.get("longitude", 0),
        timestamp
    ))

    conn.commit()
    conn.close()


# ================= RECEIVE =================
@app.route('/data', methods=['POST'])
def receive_data():

    if request.headers.get("x-api-key") != API_KEY:
        return jsonify({"error": "unauthorized"}), 403

    if not request.is_json:
        return jsonify({"error": "invalid format"}), 400

    data = request.get_json()

    insert_data(data)

    return jsonify({"status": "stored"})

# ================= GET =================
@app.route('/get', methods=['GET'])
def get_data():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sensor_data ORDER BY id DESC LIMIT 50")
    rows = cursor.fetchall()

    conn.close()

    result = []
    for row in rows:
        result.append({
            "id": row[0],
            "device_id": row[1],
            "pm1": row[2],
            "pm25": row[3],
            "pm10": row[4],
            "aqi_raw": row[5],
            "aqi_calibrated": row[6],
            "temperature": row[7],
            "humidity": row[8],
            "latitude": row[9],
            "longitude": row[10],
            "timestamp": row[11]
        })

    return jsonify(result)

@app.route('/latest_points', methods=['GET'])
def latest_points():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""

        SELECT s1.*

        FROM sensor_data s1

        INNER JOIN (

            SELECT device_id,
                   MAX(id) AS max_id

            FROM sensor_data

            GROUP BY device_id

        ) s2

        ON s1.id = s2.max_id

    """)

    rows = cursor.fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append({

            "device": row[1],
            "lat": row[9],
            "lon": row[10],
            "aqi": row[6]

        })

    return jsonify(result)
@app.route('/latest_dataframe', methods=['GET'])
def latest_dataframe():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""

        SELECT s1.*

        FROM sensor_data s1

        INNER JOIN (

            SELECT device_id,
                   MAX(id) AS max_id

            FROM sensor_data

            GROUP BY device_id

        ) s2

        ON s1.id = s2.max_id

    """)

    rows = cursor.fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append({

            "device_id": row[1],
            "aqi_calibrated": row[6],
            "latitude": row[9],
            "longitude": row[10],
            "timestamp": row[11]

        })

    return jsonify(result)
@app.route('/all_history', methods=['GET'])
def all_history():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            device_id,
            aqi_calibrated,
            latitude,
            longitude,
            timestamp
        FROM sensor_data
        ORDER BY timestamp ASC
    """)

    rows = cursor.fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append({

            "device_id": row[0],
            "aqi_calibrated": row[1],
            "latitude": row[2],
            "longitude": row[3],
            "timestamp": row[4]

        })

    return jsonify(result)
@app.route("/available_dates")
def available_dates():

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT DISTINCT DATE(timestamp)
        FROM sensor_data
        ORDER BY DATE(timestamp)
    """)

    rows = cursor.fetchall()

    conn.close()

    return jsonify([r[0] for r in rows])


@app.route("/history/<date>/<int:hour>")
def history(date, hour):

    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            device_id,
            latitude,
            longitude,
            aqi_calibrated,
            timestamp
        FROM sensor_data
        WHERE DATE(timestamp)=?
        AND strftime('%H', timestamp)=?
        ORDER BY device_id
    """, (date, f"{hour:02d}"))

    rows = cursor.fetchall()

    conn.close()

    result = []

    for row in rows:

        result.append({

            "device": row[0],
            "lat": row[1],
            "lon": row[2],
            "aqi": row[3],
            "timestamp": row[4]

        })

    return jsonify(result)

# ================= HEALTH =================
@app.route('/')
def home():
    return "AQI Server Running (IST Time Enabled)"

# ================= RUN =================
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

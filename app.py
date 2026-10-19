from flask import Flask, render_template, request, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime

app = Flask(__name__)
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "carbon_data.db"

# Simplified illustrative factors for an educational prototype.
# Replace with locally appropriate, verified factors before public/official use.
FACTORS = {
    "car_km": 0.192,       # kg CO2e per passenger-km (illustrative)
    "bike_km": 0.103,      # kg CO2e per km (illustrative petrol two-wheeler)
    "bus_km": 0.037,    # placeholder fixed below
    "train_km": 0.025,  # placeholder fixed below
    "electricity_kwh": 0.72, # kg CO2e per kWh (illustrative grid factor)
    "meat_meals": 2.5,     # kg CO2e per meal (rough illustrative factor)
    "plant_meals": 0.7     # kg CO2e per meal (rough illustrative factor)
}

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS assessments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                transport TEXT NOT NULL,
                travel_km REAL NOT NULL,
                electricity_kwh REAL NOT NULL,
                meat_meals REAL NOT NULL,
                total_kg REAL NOT NULL,
                baseline_kg REAL NOT NULL,
                saved_kg REAL NOT NULL
            )
        """)
        conn.commit()

def safe_number(data, key, default=0, minimum=0, maximum=100000):
    try:
        value = float(data.get(key, default))
        if value < minimum or value > maximum:
            raise ValueError
        return value
    except (TypeError, ValueError):
        raise ValueError(f"Please enter a valid value for {key.replace('_', ' ')} (0–{maximum}).")

def calculate(data):
    transport = data.get("transport", "car")
    if transport not in ("car", "bike", "bus", "train"):
        raise ValueError("Choose a valid transport type.")
    travel_km = safe_number(data, "travel_km", maximum=10000)
    electricity_kwh = safe_number(data, "electricity_kwh", maximum=100000)
    meat_meals = safe_number(data, "meat_meals", maximum=300)

    transport_factor = {
        "car": FACTORS["car_km"],
        "bike": FACTORS["bike_km"],
        "bus": FACTORS["bus_km"],
        "train": FACTORS["train_km"]
    }[transport]

    transport_emissions = travel_km * transport_factor
    electricity_emissions = electricity_kwh * FACTORS["electricity_kwh"]
    food_emissions = meat_meals * FACTORS["meat_meals"]
    total = transport_emissions + electricity_emissions + food_emissions

    # Example scenario: reduce travel emissions by 20%, electricity use by 10%,
    # and replace 8 meat meals with lower-impact meals (minimum 0).
    scenario_transport = transport_emissions * 0.8
    scenario_electricity = electricity_emissions * 0.9
    scenario_food = max(0, meat_meals - min(8, meat_meals)) * FACTORS["meat_meals"] + min(8, meat_meals) * FACTORS["plant_meals"]
    scenario = scenario_transport + scenario_electricity + scenario_food
    saved = max(0, total - scenario)

    tips = []
    if transport in ("car", "bike") and travel_km > 0:
        tips.append({
            "title": "Try one shared or public-transport trip",
            "detail": "Compare a bus, train, carpool or walking option for one suitable journey.",
            "impact": "Transport"
        })
    if electricity_kwh > 0:
        tips.append({
            "title": "Reduce avoidable electricity use",
            "detail": "Switch off idle devices and use efficient lighting; check your next bill to track change.",
            "impact": "Home energy"
        })
    if meat_meals > 0:
        tips.append({
            "title": "Try a lower-impact meal",
            "detail": "Replace a few meat-based meals with plant-rich alternatives if suitable for your diet.",
            "impact": "Food"
        })
    if not tips:
        tips.append({
            "title": "Keep tracking your footprint",
            "detail": "Add monthly travel, electricity and food data to get more tailored suggestions.",
            "impact": "Getting started"
        })

    return {
        "transport_emissions": round(transport_emissions, 2),
        "electricity_emissions": round(electricity_emissions, 2),
        "food_emissions": round(food_emissions, 2),
        "total_kg": round(total, 2),
        "scenario_kg": round(scenario, 2),
        "saved_kg": round(saved, 2),
        "reduction_percent": round((saved / total * 100) if total else 0, 1),
        "tips": tips,
        "disclaimer": "Estimates use simplified illustrative factors and are for learning only, not an official carbon inventory."
    }

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/calculate", methods=["POST"])
def api_calculate():
    try:
        data = request.get_json(force=True)
        result = calculate(data)
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                INSERT INTO assessments
                (created_at, transport, travel_km, electricity_kwh, meat_meals, total_kg, baseline_kg, saved_kg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now().isoformat(timespec="seconds"),
                data.get("transport", "car"),
                float(data.get("travel_km", 0)),
                float(data.get("electricity_kwh", 0)),
                float(data.get("meat_meals", 0)),
                result["total_kg"],
                result["total_kg"],
                result["saved_kg"]
            ))
            conn.commit()
        return jsonify(result)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception:
        app.logger.exception("Calculation failed")
        return jsonify({"error": "Something went wrong. Check your entries and try again."}), 500

@app.route("/api/history")
def api_history():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT created_at, total_kg, saved_kg FROM assessments
            ORDER BY id DESC LIMIT 7
        """).fetchall()
    return jsonify([
        {"date": row[0][:10], "total_kg": row[1], "saved_kg": row[2]}
        for row in rows
    ][::-1])

init_db()

if __name__ == "__main__":
    app.run(debug=True)

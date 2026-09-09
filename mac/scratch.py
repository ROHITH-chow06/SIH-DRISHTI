import pytest
from fastapi.testclient import TestClient
from api.telemetry_server import app, alert_log, add_alert, vehicle_anchors
import api.telemetry_server as ts
from mapping.living_map import LivingMap
from core.config import SAR_ANCHOR_LAT, SAR_ANCHOR_LON

client = TestClient(app)

# Reset state
alert_log.clear()
vehicle_anchors.clear()
ts.living_map = LivingMap(on_alert=add_alert)

print("Before:", [r.status for r in ts.living_map._candidate_routes.values()])
print("on_alert callback exists:", ts.living_map.on_alert is not None)

routes_res = client.get("/api/map/routes")
routes = routes_res.json()
p1 = routes[0]["path_coordinates"][0]

print("Sending anchor:", SAR_ANCHOR_LAT, SAR_ANCHOR_LON)
client.post("/api/telemetry", json={
    "vehicle_id": "V1",
    "latitude": SAR_ANCHOR_LAT,
    "longitude": SAR_ANCHOR_LON,
    "altitude": 0,
    "speed_kmh": 0
})
print("Alerts after anchor:", [a.message for a in alert_log])

print("Sending p1:", p1["latitude"], p1["longitude"])
client.post("/api/telemetry", json={
    "vehicle_id": "V1",
    "latitude": p1["latitude"],
    "longitude": p1["longitude"],
    "altitude": 0,
    "speed_kmh": 10
})
print("Alerts after p1:", [a.message for a in alert_log])

print("After:", [r.status for r in ts.living_map._candidate_routes.values()])

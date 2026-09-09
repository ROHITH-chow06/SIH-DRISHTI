import pytest
from fastapi.testclient import TestClient
import api.telemetry_server as ts
from api.telemetry_server import app

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_state():
    ts.vehicle_anchors.clear()
    ts.latest_telemetry_store.clear()
    ts.nav_engine = ts.NavigationEngine(ts.living_map)
    ts.nav_engine = ts.NavigationEngine(ts.living_map)
    ts.nav_engine.navigation_radius_m = 500.0
    ts.nav_engine.virtual_mode = True
    ts.nav_engine.projector.movement_threshold = 2.0
    yield

from datetime import datetime

def _send_gps(vid, lat, lon, speed=10):
    res = client.post("/api/telemetry", json={
        "vehicle_id": vid,
        "latitude": lat,
        "longitude": lon,
        "altitude": 0,
        "speed_kmh": speed,
        "heading_deg": 90,
        "timestamp": datetime.utcnow().isoformat()
    })
    if res.status_code != 200:
        print("ERROR POSTING TELEMETRY:", res.json())
        res.raise_for_status()

def test_01_virtual_mode_starts_at_loading_area():
    _send_gps("TRUCK_1", 18.682072, 81.193572)
    client.post("/api/navigation/vehicle", json={"vehicle_id": "TRUCK_1"})
    
    state = client.get("/api/navigation/state").json()
    assert state["projection_mode"] == "DEMO_VIRTUAL_MINE"
    assert state["road_type"] == "HAUL"
    assert state["current_position"]["latitude"] == 18.682072
    assert state["current_position"]["longitude"] == 81.193572
    assert state["data_sources"]["gps"] == "DEMO_VIRTUAL_MINE"

def test_02_raw_gps_remains_unchanged():
    _send_gps("TRUCK_1", 18.682072, 81.193572)
    client.post("/api/navigation/vehicle", json={"vehicle_id": "TRUCK_1"})
    
    # Virtual position is at 18.6820, 81.1930
    # But raw telemetry should still be the original
    raw = ts.latest_telemetry_store["TRUCK_1"]
    assert raw.position.latitude == 18.682072
    assert raw.position.longitude == 81.193572

def test_03_movement_below_threshold_ignored():
    _send_gps("TRUCK_1", 18.6820, 81.1930)
    client.post("/api/navigation/vehicle", json={"vehicle_id": "TRUCK_1"})
    
    client.get("/api/navigation/state")
    state1 = client.get("/api/navigation/virtual-state").json()[0]
    prog1 = state1["route_progress_m"]
    
    # Move 1 meter (less than 2.0m threshold)
    # 1 degree lat is ~111km -> 1m is ~0.000009
    _send_gps("TRUCK_1", 18.6820 + 0.000009, 81.1930)
    
    client.get("/api/navigation/state")
    state2 = client.get("/api/navigation/virtual-state").json()[0]
    assert state2["route_progress_m"] == prog1 # Unchanged

def test_04_meaningful_movement_advances_route():
    _send_gps("TRUCK_1", 18.6820, 81.1930)
    client.post("/api/navigation/vehicle", json={"vehicle_id": "TRUCK_1"})
    
    client.get("/api/navigation/state")
    state1 = client.get("/api/navigation/virtual-state").json()[0]
    assert state1["route_progress_m"] == 0.0
    
    # Move ~50 meters physical
    _send_gps("TRUCK_1", 18.6820 + 0.00045, 81.1930)
    
    client.get("/api/navigation/state")
    state2 = client.get("/api/navigation/virtual-state").json()[0]
    assert state2["route_progress_m"] >= 45.0 # Should advance by ~50m

def test_05_ghat_road_indicator():
    _send_gps("TRUCK_1", 18.6820, 81.1930)
    client.post("/api/navigation/vehicle", json={"vehicle_id": "TRUCK_1"})
    client.post("/api/navigation/virtual-destination", json={"destination_name": "FACE ACCESS"})
    
    state = client.get("/api/navigation/state").json()
    assert state["road_type"] == "GHAT"
    assert state["gradient_percent"] == 8.5

def test_06_destination_switch_preserves_position():
    _send_gps("TRUCK_1", 18.6820, 81.1930)
    client.post("/api/navigation/vehicle", json={"vehicle_id": "TRUCK_1"})
    
    # Move ~100m on LOADING AREA
    _send_gps("TRUCK_1", 18.6820 + 0.0009, 81.1930)
    
    client.get("/api/navigation/state")
    state1 = client.get("/api/navigation/virtual-state").json()[0]
    pos1 = state1["virtual_position"]
    
    # Switch destination
    client.post("/api/navigation/virtual-destination", json={"destination_name": "FACE ACCESS"})
    
    # Get state again
    client.get("/api/navigation/state")
    
    state2 = client.get("/api/navigation/virtual-state").json()[0]
    pos2 = state2["virtual_position"]
    
    assert state2["route_id"] == "FACE ACCESS"
    # Since it snaps to the closest point on a complex hairpin, it shouldn't drift significantly
    assert abs(pos1["latitude"] - pos2["latitude"]) < 0.005
    assert abs(pos1["longitude"] - pos2["longitude"]) < 0.005

def test_07_virtual_reset():
    _send_gps("TRUCK_1", 18.6820, 81.1930)
    client.post("/api/navigation/vehicle", json={"vehicle_id": "TRUCK_1"})
    client.get("/api/navigation/state") # Initialize projector
    
    _send_gps("TRUCK_1", 18.6830, 81.1930) # ~111m
    
    client.get("/api/navigation/state")
    state1 = client.get("/api/navigation/virtual-state").json()[0]
    assert state1["route_progress_m"] > 50
    
    client.post("/api/navigation/virtual-reset")
    
    # Need to trigger update
    client.get("/api/navigation/state")
    state2 = client.get("/api/navigation/virtual-state").json()[0]
    assert state2["route_progress_m"] == 0.0

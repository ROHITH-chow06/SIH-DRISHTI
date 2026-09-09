import pytest
from datetime import datetime
from pydantic import ValidationError
from fastapi.testclient import TestClient

from core.models import VehicleTelemetry, Position, Motion, Metadata, VehicleSensors, State
from sources.simulation_source import SimulationDataSource
from api.telemetry_server import app, latest_telemetry_store, living_map

client = TestClient(app)

@pytest.fixture(autouse=True)
def clear_store():
    """Clear the in-memory store and living map traces before each test."""
    import api.telemetry_server as ts
    ts.GPS_DISPLAY_MODE = "real"
    ts.vehicle_anchors.clear()
    latest_telemetry_store.clear()
    living_map._vehicle_traces.clear()
    living_map._accumulated_road_corridor.clear()

def test_1_vehicle_telemetry_creation():
    """Test 1: VehicleTelemetry creation with missing optionals defaults properly."""
    telemetry = VehicleTelemetry(
        vehicle_id="TRUCK_01",
        timestamp=datetime.utcnow(),
        position=Position(latitude=10.0, longitude=20.0),
        motion=Motion()
    )
    assert telemetry.vehicle_id == "TRUCK_01"
    assert telemetry.vehicle_sensors.radar_distance_m is None
    assert telemetry.state.brake_active is None

def test_2_valid_gps_data():
    """Test 2: Valid GPS data models correctly."""
    pos = Position(latitude=10.0, longitude=20.0, altitude=50.0)
    assert pos.latitude == 10.0
    
def test_3_invalid_latitude():
    """Test 3: Invalid latitude ranges."""
    with pytest.raises(ValidationError):
        Position(latitude=100.0, longitude=20.0)
    with pytest.raises(ValidationError):
        Position(latitude=-100.0, longitude=20.0)

def test_4_invalid_longitude():
    """Test 4: Invalid longitude ranges."""
    with pytest.raises(ValidationError):
        Position(latitude=10.0, longitude=200.0)
    with pytest.raises(ValidationError):
        Position(latitude=10.0, longitude=-200.0)

def test_5_negative_speed():
    """Test 5: Negative speed validation."""
    with pytest.raises(ValidationError):
        Motion(speed_kmh=-5.0)

def test_6_missing_optional_sensor_values():
    """Test 6: Missing optional sensor values should just be None."""
    sensors = VehicleSensors()
    assert sensors.acceleration_x is None
    assert sensors.barometric_altitude_m is None

def test_7_multiple_vehicles_api():
    """Test 7 & 8: Multiple vehicles and POST /api/telemetry."""
    data1 = {
        "vehicle_id": "TRUCK_01",
        "latitude": 17.3850,
        "longitude": 78.4867,
        "timestamp": datetime.utcnow().isoformat()
    }
    data2 = {
        "vehicle_id": "TRUCK_02",
        "latitude": 17.3851,
        "longitude": 78.4868,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    res1 = client.post("/api/telemetry", json=data1)
    assert res1.status_code == 200
    
    res2 = client.post("/api/telemetry", json=data2)
    assert res2.status_code == 200

    # Test 9: GET /api/vehicles
    res3 = client.get("/api/vehicles")
    assert res3.status_code == 200
    assert len(res3.json()) == 2

def test_10_get_single_vehicle():
    """Test 10: GET /api/vehicles/{vehicle_id}"""
    data = {
        "vehicle_id": "TRUCK_03",
        "latitude": 12.0,
        "longitude": 70.0,
        "timestamp": datetime.utcnow().isoformat()
    }
    client.post("/api/telemetry", json=data)
    
    res = client.get("/api/vehicles/TRUCK_03")
    assert res.status_code == 200
    assert res.json()["vehicle_id"] == "TRUCK_03"
    
    res_not_found = client.get("/api/vehicles/UNKNOWN")
    assert res_not_found.status_code == 404

def test_11_invalid_telemetry_request():
    """Test 11: Invalid telemetry request returns HTTP error."""
    data = {
        "vehicle_id": "TRUCK_04",
        "latitude": 100.0, # Invalid lat
        "longitude": 78.4867,
        "timestamp": datetime.utcnow().isoformat()
    }
    res = client.post("/api/telemetry", json=data)
    assert res.status_code == 422 # Unprocessable Entity

def test_12_simulation_data_source():
    """Test 12: SimulationDataSource."""
    sim = SimulationDataSource("TEST_SIM")
    telemetry = sim.get_latest_telemetry()
    assert telemetry is not None
    assert telemetry.vehicle_id == "TEST_SIM"
    assert telemetry.metadata.position_source == "SIMULATION"
    assert telemetry.metadata.sensor_source == "SIMULATION"

def test_13_map_endpoints_and_living_map_integration():
    """Test 13: Verify POST telemetry updates LivingMap and map endpoints return position and trace."""
    p1 = {
        "vehicle_id": "TRUCK_10",
        "latitude": 17.1000,
        "longitude": 78.1000,
        "timestamp": datetime.utcnow().isoformat()
    }
    p2 = {
        "vehicle_id": "TRUCK_10",
        "latitude": 17.1005,
        "longitude": 78.1005,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Post telemetry update 1
    res1 = client.post("/api/telemetry", json=p1)
    assert res1.status_code == 200

    # Verify /api/map/vehicles
    res_map = client.get("/api/map/vehicles")
    assert res_map.status_code == 200
    assert "TRUCK_10" in res_map.json()
    assert res_map.json()["TRUCK_10"]["latitude"] == 17.1000

    # Post telemetry update 2
    res2 = client.post("/api/telemetry", json=p2)
    assert res2.status_code == 200

    # Verify current position is updated to position 2
    res_map_2 = client.get("/api/map/vehicles")
    assert res_map_2.json()["TRUCK_10"]["latitude"] == 17.1005

    # Verify trace contains both points
    res_trace = client.get("/api/map/trace/TRUCK_10")
    assert res_trace.status_code == 200
    trace = res_trace.json()
    assert len(trace) == 2
    assert trace[0]["latitude"] == 17.1000
    assert trace[1]["latitude"] == 17.1005

def test_14_multiple_vehicles_map_isolation():
    """Test 14: Multiple vehicles stay isolated on map endpoints."""
    client.post("/api/telemetry", json={
        "vehicle_id": "TRUCK_A",
        "latitude": 10.0,
        "longitude": 20.0,
        "timestamp": datetime.utcnow().isoformat()
    })
    client.post("/api/telemetry", json={
        "vehicle_id": "TRUCK_B",
        "latitude": 30.0,
        "longitude": 40.0,
        "timestamp": datetime.utcnow().isoformat()
    })

    res_map = client.get("/api/map/vehicles")
    assert res_map.status_code == 200
    assert "TRUCK_A" in res_map.json()
    assert "TRUCK_B" in res_map.json()

    trace_a = client.get("/api/map/trace/TRUCK_A").json()
    trace_b = client.get("/api/map/trace/TRUCK_B").json()
    assert len(trace_a) == 1
    assert len(trace_b) == 1
    assert trace_a[0]["latitude"] == 10.0
    assert trace_b[0]["latitude"] == 30.0

def test_15_unknown_vehicle_trace_error():
    """Test 15: Requesting trace for unknown vehicle returns 404."""
    res = client.get("/api/map/trace/NONEXISTENT_VEHICLE")
    assert res.status_code == 404
    assert res.json()["detail"] == "Vehicle trace not found"

def test_16_serve_living_map_page():
    """Test 16: GET /map returns the HTML Living Map page."""
    res = client.get("/map")
    assert res.status_code == 200
    assert "DRISHTI LIVING MAP" in res.text

def test_17_road_corridor_endpoint():
    """Test 17: GET /api/map/road_corridors returns the accumulated corridor."""
    import api.telemetry_server as ts
    from mapping.living_map import LivingMap
    ts.living_map = LivingMap()
    
    client.post("/api/telemetry", json={
        "vehicle_id": "TRUCK_X",
        "latitude": 17.0,
        "longitude": 78.0,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    res = client.get("/api/map/road_corridors")
    assert res.status_code == 200
    corridors = res.json()
    assert len(corridors) == 1
    assert corridors[0]["latitude"] == 17.0
    assert "confidence" in corridors[0]
    assert "is_stale" in corridors[0]

def test_18_sar_metadata_endpoint():
    """Test 18: GET /api/map/sar/metadata returns SAR metadata."""
    res = client.get("/api/map/sar/metadata")
    assert res.status_code == 200
    data = res.json()
    assert data["product_id"] == "S1D_IW_GRDH_1SDV_20260829T002946_20260829T003011_004333_007FEA_20B4_COG.SAFE"
    assert data["polarization"] == "VV+VH"

def test_19_demo_anchored_gps_mode():
    """Test 19: Demo anchored GPS mode transformation math."""
    import api.telemetry_server as ts
    from core.config import SAR_ANCHOR_LAT, SAR_ANCHOR_LON
    import math
    
    # Enable demo mode temporarily
    original_mode = ts.GPS_DISPLAY_MODE
    ts.GPS_DISPLAY_MODE = "demo_anchored"
    ts.vehicle_anchors.clear()
    
    # 1. First GPS point establishes vehicle origin
    res1 = client.post("/api/telemetry", json={
        "vehicle_id": "DEMO_TRUCK_1",
        "latitude": 10.0,
        "longitude": 20.0,
        "timestamp": datetime.utcnow().isoformat()
    })
    assert res1.status_code == 200
    d1 = res1.json()
    assert d1["position"]["latitude"] == SAR_ANCHOR_LAT
    assert d1["position"]["longitude"] == SAR_ANCHOR_LON
    
    # 2. Second GPS point 10m north -> approx 10m north relative to SAR anchor
    # 10m north is delta_lat = 10.0 / 111320.0
    lat_10m = 10.0 + (10.0 / 111320.0)
    res2 = client.post("/api/telemetry", json={
        "vehicle_id": "DEMO_TRUCK_1",
        "latitude": lat_10m,
        "longitude": 20.0,
        "timestamp": datetime.utcnow().isoformat()
    })
    d2 = res2.json()
    assert pytest.approx(d2["position"]["latitude"], abs=1e-6) == SAR_ANCHOR_LAT + (10.0 / 111320.0)
    assert d2["position"]["longitude"] == SAR_ANCHOR_LON
    
    # 3. Third GPS point 10m east -> approx 10m east
    # 10m east at lat 10.0 is delta_lon = 10.0 / (111320.0 * cos(10deg))
    lon_10m = 20.0 + (10.0 / (111320.0 * math.cos(math.radians(10.0))))
    res3 = client.post("/api/telemetry", json={
        "vehicle_id": "DEMO_TRUCK_1",
        "latitude": 10.0,
        "longitude": lon_10m,
        "timestamp": datetime.utcnow().isoformat()
    })
    d3 = res3.json()
    assert d3["position"]["latitude"] == SAR_ANCHOR_LAT
    expected_lon_shift = 10.0 / (111320.0 * math.cos(math.radians(SAR_ANCHOR_LAT)))
    assert pytest.approx(d3["position"]["longitude"], abs=1e-6) == SAR_ANCHOR_LON + expected_lon_shift
    
    # 4. Original phone GPS remains unchanged
    assert d3["metadata"]["original_position"]["latitude"] == 10.0
    assert d3["metadata"]["original_position"]["longitude"] == lon_10m
    
    # 5 & 6. Multiple vehicles have independent origins but share Deposit-5 display
    res_b1 = client.post("/api/telemetry", json={
        "vehicle_id": "DEMO_TRUCK_2",
        "latitude": 50.0, # Completely different origin
        "longitude": 60.0,
        "timestamp": datetime.utcnow().isoformat()
    })
    db1 = res_b1.json()
    assert db1["position"]["latitude"] == SAR_ANCHOR_LAT
    assert db1["position"]["longitude"] == SAR_ANCHOR_LON
    assert db1["metadata"]["original_position"]["latitude"] == 50.0

    # Restore
    ts.GPS_DISPLAY_MODE = original_mode



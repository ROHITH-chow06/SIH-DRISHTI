import pytest
from datetime import datetime, timedelta
import time
from fastapi.testclient import TestClient

from api.telemetry_server import app
from core.models import CandidateRoadSegment, Position
import api.telemetry_server as ts
from mapping.living_map import LivingMap
from mapping.route_source import DemoRouteSource, extract_candidate_routes_from_sar

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_state():
    ts.GPS_DISPLAY_MODE = "real"
    ts.vehicle_anchors.clear()
    ts.latest_telemetry_store.clear()
    if ts.living_map:
        ts.living_map._last_meaningful_observation_pos.clear()
    yield

def test_1_candidate_routes_load():
    source = DemoRouteSource()
    routes = source.load_routes()
    assert len(routes) == 3
    assert routes[0].route_id == "DEMO_HAUL_MAIN_01"

def test_2_routes_inside_deposit_5():
    source = DemoRouteSource()
    routes = source.load_routes()
    for route in routes:
        for pt in route.path_coordinates:
            assert 18.6668167 <= pt.latitude <= 18.6973278
            assert 81.1782861 <= pt.longitude <= 81.2088583

def test_3_multiple_route_segments():
    source = DemoRouteSource()
    assert len(source.load_routes()) > 1

def test_4_vehicle_near_route_is_associated():
    ts.living_map = LivingMap()
    
    # Send GPS right on the route
    res = client.post("/api/telemetry", json={
        "vehicle_id": "TEST_TRUCK",
        "latitude": 18.682072, # Exactly on DEMO_HAUL_MAIN_01
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    routes = ts.living_map.get_candidate_routes()
    r = next(rt for rt in routes if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert r.status == "VALIDATED"
    assert r.confidence == 0.2 # Base 0.1 + 0.1
    assert "TEST_TRUCK" in r.nearest_vehicle_ids

def test_5_route_confidence_increases():
    ts.living_map = LivingMap()
    
    routes = ts.living_map.get_candidate_routes()
    r = next(rt for rt in routes if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert r.confidence == 0.1
    
    client.post("/api/telemetry", json={
        "vehicle_id": "TEST_TRUCK",
        "latitude": 18.682072, 
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    routes2 = ts.living_map.get_candidate_routes()
    r2 = next(rt for rt in routes2 if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert r2.confidence == 0.2

def test_6_multiple_vehicles_validate():
    ts.living_map = LivingMap()
    
    client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": 18.682072, 
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    client.post("/api/telemetry", json={
        "vehicle_id": "V2",
        "latitude": 18.682072, 
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    routes = ts.living_map.get_candidate_routes()
    r = next(rt for rt in routes if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert pytest.approx(r.confidence, 0.01) == 0.3
    assert "V1" in r.nearest_vehicle_ids
    assert "V2" in r.nearest_vehicle_ids

def test_7_raw_gps_unchanged():
    ts.living_map = LivingMap()
    
    res = client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": 18.682075, # slightly off
        "longitude": 81.193575,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    d = res.json()
    assert d["position"]["latitude"] == 18.682075
    
def test_8_demo_anchored_gps_works_with_routes():
    original_mode = ts.GPS_DISPLAY_MODE
    ts.GPS_DISPLAY_MODE = "demo_anchored"
    ts.vehicle_anchors.clear()
    ts.living_map = LivingMap()
    
    # 1. establish anchor
    client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": 10.0,
        "longitude": 20.0,
        "timestamp": datetime.utcnow().isoformat()
    })
    # transformed point should be at 18.682072, 81.193572
    
    routes = ts.living_map.get_candidate_routes()
    r = next(rt for rt in routes if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert r.status == "VALIDATED"
    
    ts.GPS_DISPLAY_MODE = original_mode

def test_9_routes_available_no_vehicles():
    ts.living_map = LivingMap()
    routes = ts.living_map.get_candidate_routes()
    assert len(routes) > 0

def test_10_stale_route_state():
    ts.living_map = LivingMap()
    
    client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": 18.682072, 
        "longitude": 81.193572,
        "timestamp": (datetime.utcnow() - timedelta(minutes=10)).isoformat() # 10 mins ago
    })
    
    routes = ts.living_map.get_candidate_routes()
    r = next(rt for rt in routes if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert r.status == "STALE"

def test_11_api_returns_routes():
    res = client.get("/api/map/routes")
    assert res.status_code == 200
    assert len(res.json()) > 0

def test_12_api_returns_single_route():
    res = client.get("/api/map/routes/DEMO_HAUL_MAIN_01")
    assert res.status_code == 200
    assert res.json()["route_id"] == "DEMO_HAUL_MAIN_01"

def test_13_existing_map_remains():
    res = client.get("/map")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]

def test_14_provenance_preserved():
    res = client.get("/api/map/routes/DEMO_HAUL_MAIN_01")
    data = res.json()
    assert data["source"] == "DEMO_CANDIDATE"

def test_15_sar_hook():
    with pytest.raises(NotImplementedError):
        extract_candidate_routes_from_sar("test.tif")

def test_16_repeated_stationary_gps():
    ts.living_map = LivingMap()
    
    # 1. First point
    client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": 18.682072, 
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    routes = ts.living_map.get_candidate_routes()
    r1 = next(rt for rt in routes if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert r1.confidence == 0.2
    
    # 2. Second point (same)
    client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": 18.682072, 
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    routes2 = ts.living_map.get_candidate_routes()
    r2 = next(rt for rt in routes2 if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert r2.confidence == 0.2 # Should NOT increase!

def test_17_movement_counts_as_meaningful():
    ts.living_map = LivingMap()
    
    # 1. First point
    client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": 18.682072, 
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    # 2. Move ~10m north
    # 1 degree lat = 111320m, 10m = 10 / 111320 = 0.000089
    lat_10m = 18.682072 + 0.00009
    
    client.post("/api/telemetry", json={
        "vehicle_id": "V1",
        "latitude": lat_10m, 
        "longitude": 81.193572,
        "timestamp": datetime.utcnow().isoformat()
    })
    
    routes = ts.living_map.get_candidate_routes()
    r = next(rt for rt in routes if rt.route_id == "DEMO_HAUL_MAIN_01")
    assert pytest.approx(r.confidence, 0.01) == 0.3 # Increased because we moved!

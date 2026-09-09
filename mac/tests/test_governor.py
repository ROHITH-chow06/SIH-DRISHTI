from datetime import datetime
from fastapi.testclient import TestClient
from api.telemetry_server import app
from core.models import SimulatorConditions, GovernorDecision
from core.governor import calculate_safe_speed
import api.telemetry_server as ts

client = TestClient(app)

def test_1_clear_dry_is_30():
    c = SimulatorConditions(visibility="CLEAR", road="DRY", obstacle="NONE")
    d = calculate_safe_speed(c)
    assert d.final_speed_limit_kmh == 30.0
    assert d.visibility_limit_kmh == 30.0
    assert d.road_condition_limit_kmh == 30.0
    assert d.state == "CLEAR"

def test_2_fog_dry_is_10():
    c = SimulatorConditions(visibility="FOG", road="DRY", obstacle="NONE")
    d = calculate_safe_speed(c)
    assert d.final_speed_limit_kmh == 10.0
    assert d.visibility_limit_kmh == 10.0
    assert d.road_condition_limit_kmh == 30.0
    assert d.state == "SLOW"

def test_3_clear_wet_is_15():
    c = SimulatorConditions(visibility="CLEAR", road="WET", obstacle="NONE")
    d = calculate_safe_speed(c)
    assert d.final_speed_limit_kmh == 15.0
    assert d.visibility_limit_kmh == 30.0
    assert d.road_condition_limit_kmh == 15.0
    assert d.state == "CAUTION"

def test_4_fog_wet_is_10():
    c = SimulatorConditions(visibility="FOG", road="WET", obstacle="NONE")
    d = calculate_safe_speed(c)
    assert d.final_speed_limit_kmh == 10.0
    assert d.visibility_limit_kmh == 10.0
    assert d.road_condition_limit_kmh == 15.0
    assert d.state == "SLOW"

def test_5_obstacle_is_stop():
    c = SimulatorConditions(visibility="CLEAR", road="DRY", obstacle="PEDESTRIAN")
    d = calculate_safe_speed(c)
    assert d.final_speed_limit_kmh == 0.0
    assert d.state == "STOP"
    assert "Obstacle detected" in d.reason

def test_6_api_simulator_state():
    res = client.get("/api/simulator/state")
    assert res.status_code == 200
    assert res.json()["visibility"] in ["CLEAR", "FOG"]

def test_7_api_update_conditions():
    res = client.post("/api/simulator/conditions", json={
        "visibility": "FOG",
        "road": "WET",
        "obstacle": "NONE"
    })
    assert res.status_code == 200
    assert res.json()["visibility"] == "FOG"
    
    # check governor output updates
    res2 = client.get("/api/governor/state")
    assert res2.status_code == 200
    assert res2.json()["final_speed_limit_kmh"] == 10.0
    assert res2.json()["state"] == "SLOW"

def test_8_ui_simulator_page_loads():
    res = client.get("/simulator")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]

import pytest
from core.models import SimulatorConditions, NearbyVehicle, SafetyAlert
from core.safety import StoppingDistanceModel, VehicleConflictEvaluator, TurnEvaluator, DualConstraintGovernor

def test_01_clear_dry_is_30():
    conditions = SimulatorConditions(visibility="CLEAR", road="DRY", obstacle="NONE")
    decision = DualConstraintGovernor.calculate_safe_speed(conditions, current_speed_kmh=15.0, nearby_vehicles=[], next_maneuver="STRAIGHT")
    assert decision.permitted_speed_kmh == 30.0
    assert decision.active_alert.alert_type == "CLEAR"

def test_02_wet_is_reduced():
    conditions = SimulatorConditions(visibility="CLEAR", road="WET", obstacle="NONE")
    decision = DualConstraintGovernor.calculate_safe_speed(conditions, current_speed_kmh=15.0, nearby_vehicles=[], next_maneuver="STRAIGHT")
    assert decision.permitted_speed_kmh == 15.0
    assert "WET_ROAD" in decision.constraints

def test_03_fog_is_reduced():
    conditions = SimulatorConditions(visibility="FOG", road="DRY", obstacle="NONE")
    decision = DualConstraintGovernor.calculate_safe_speed(conditions, current_speed_kmh=15.0, nearby_vehicles=[], next_maneuver="STRAIGHT")
    assert decision.permitted_speed_kmh == 10.0
    assert decision.active_alert.alert_type == "FOG"

def test_04_fog_wet_is_most_restrictive():
    conditions = SimulatorConditions(visibility="FOG", road="WET", obstacle="NONE")
    decision = DualConstraintGovernor.calculate_safe_speed(conditions, current_speed_kmh=15.0, nearby_vehicles=[], next_maneuver="STRAIGHT")
    assert decision.permitted_speed_kmh == 10.0

def test_05_critical_obstacle_is_stop():
    conditions = SimulatorConditions(visibility="CLEAR", road="DRY", obstacle="OBSTACLE")
    decision = DualConstraintGovernor.calculate_safe_speed(conditions, current_speed_kmh=30.0, nearby_vehicles=[], next_maneuver="STRAIGHT")
    assert decision.permitted_speed_kmh == 0.0
    assert decision.active_alert.alert_type == "STOP"
    assert decision.active_alert.severity == "CRITICAL"

def test_06_pedestrian_far_away():
    conditions = SimulatorConditions(visibility="CLEAR", road="DRY", obstacle="PEDESTRIAN")
    decision = DualConstraintGovernor.calculate_safe_speed(conditions, current_speed_kmh=0.0, nearby_vehicles=[], next_maneuver="STRAIGHT")
    assert decision.permitted_speed_kmh == 10.0
    assert decision.active_alert.alert_type == "PEDESTRIAN"
    assert decision.active_alert.severity == "WARNING"

def test_08_vehicle_far_away():
    nv = NearbyVehicle(vehicle_id="TRUCK2", distance_m=400.0, bearing_deg=0.0, relative_direction="FRONT", speed_kmh=20.0, heading_deg=0.0)
    limit, alert = VehicleConflictEvaluator.evaluate(current_speed_kmh=30.0, nearby_vehicles=[nv])
    assert limit is None
    assert alert is None

def test_10_closing_vehicle():
    nv = NearbyVehicle(vehicle_id="TRUCK2", distance_m=40.0, bearing_deg=0.0, relative_direction="FRONT", speed_kmh=20.0, heading_deg=180.0)
    limit, alert = VehicleConflictEvaluator.evaluate(current_speed_kmh=0.0, nearby_vehicles=[nv])
    assert limit == 12.0
    assert alert.severity == "WARNING"

def test_11_critical_vehicle_conflict():
    nv = NearbyVehicle(vehicle_id="TRUCK2", distance_m=20.0, bearing_deg=0.0, relative_direction="FRONT", speed_kmh=0.0, heading_deg=180.0)
    limit, alert = VehicleConflictEvaluator.evaluate(current_speed_kmh=30.0, nearby_vehicles=[nv])
    assert limit == 0.0
    assert alert.severity == "CRITICAL"

def test_12_sharp_turn():
    limit, alert = TurnEvaluator.evaluate("SHARP RIGHT")
    assert limit == 15.0
    assert alert.alert_type == "SHARP TURN"

def test_13_fog_and_turn():
    conditions = SimulatorConditions(visibility="FOG", road="DRY", obstacle="NONE")
    decision = DualConstraintGovernor.calculate_safe_speed(conditions, current_speed_kmh=15.0, nearby_vehicles=[], next_maneuver="SHARP RIGHT")
    assert decision.permitted_speed_kmh == 10.0

def test_19_stopping_distance_si_units():
    sd = StoppingDistanceModel.calculate_stopping_distance(speed_kmh=36.0)
    assert round(sd, 2) == 36.67

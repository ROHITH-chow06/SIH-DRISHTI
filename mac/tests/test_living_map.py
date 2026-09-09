import pytest
from datetime import datetime
from core.models import VehicleTelemetry, Position, Motion, Metadata, VehicleSensors, State
from mapping.living_map import LivingMap

def create_sample_telemetry(vehicle_id: str, lat: float, lon: float, alt: float = 500.0) -> VehicleTelemetry:
    return VehicleTelemetry(
        vehicle_id=vehicle_id,
        timestamp=datetime.utcnow(),
        position=Position(latitude=lat, longitude=lon, altitude=alt),
        motion=Motion(speed_kmh=10.0, heading_deg=45.0),
        vehicle_sensors=VehicleSensors(),
        state=State(),
        metadata=Metadata(position_source="PHONE_GPS", confidence="HIGH")
    )

def test_empty_living_map():
    living_map = LivingMap()
    assert living_map.get_tracked_vehicles() == []
    assert living_map.get_current_positions() == {}
    assert living_map.get_point_count("TRUCK_01") == 0
    assert living_map.get_vehicle_trace("TRUCK_01") == []

def test_single_vehicle_update():
    living_map = LivingMap()
    t1 = create_sample_telemetry("TRUCK_01", 17.3850, 78.4867)
    t2 = create_sample_telemetry("TRUCK_01", 17.3851, 78.4868)
    
    living_map.update_vehicle(t1)
    assert living_map.get_point_count("TRUCK_01") == 1
    assert living_map.get_current_positions()["TRUCK_01"].latitude == 17.3850

    living_map.update_vehicle(t2)
    assert living_map.get_point_count("TRUCK_01") == 2
    assert living_map.get_current_positions()["TRUCK_01"].latitude == 17.3851

    trace = living_map.get_vehicle_trace("TRUCK_01")
    assert len(trace) == 2
    assert trace[0].latitude == 17.3850
    assert trace[1].latitude == 17.3851

def test_multiple_vehicle_traces():
    living_map = LivingMap()
    t1_truck1 = create_sample_telemetry("TRUCK_01", 17.3850, 78.4867)
    t2_truck1 = create_sample_telemetry("TRUCK_01", 17.3855, 78.4870)
    t1_truck2 = create_sample_telemetry("TRUCK_02", 20.0000, 75.0000)

    living_map.update_vehicle(t1_truck1)
    living_map.update_vehicle(t1_truck2)
    living_map.update_vehicle(t2_truck1)

    tracked = living_map.get_tracked_vehicles()
    assert "TRUCK_01" in tracked
    assert "TRUCK_02" in tracked
    assert len(tracked) == 2

    assert living_map.get_point_count("TRUCK_01") == 2
    assert living_map.get_point_count("TRUCK_02") == 1

    positions = living_map.get_current_positions()
    assert positions["TRUCK_01"].latitude == 17.3855
    assert positions["TRUCK_02"].latitude == 20.0000

def test_extension_points():
    living_map = LivingMap()
    # Extension points should run safely without error
    living_map.update_drone_layer({})
    living_map.update_sar_validation({})
    living_map.update_road_corridors({})
    living_map.update_radar_obstacles({})

def test_road_corridor_accumulation():
    from core.config import ROAD_CORRIDOR_MIN_DISTANCE_M
    living_map = LivingMap()
    
    # Base point
    t1 = create_sample_telemetry("TRUCK_01", 17.0000, 78.0000)
    living_map.update_vehicle(t1)
    
    # Point very close to base point (e.g. 1 meter away), should be ignored by corridor threshold
    # 0.00001 deg lat is approx 1.1 meters
    t2 = create_sample_telemetry("TRUCK_01", 17.00001, 78.0000)
    living_map.update_vehicle(t2)
    
    # Point far away, should be added
    # 0.001 deg lat is approx 111 meters
    t3 = create_sample_telemetry("TRUCK_02", 17.0010, 78.0000)
    living_map.update_vehicle(t3)
    
    corridors = living_map.get_road_corridors()
    assert len(corridors) == 2
    assert corridors[0].latitude == 17.0000
    assert corridors[1].latitude == 17.0010

def test_road_corridor_staleness_and_confidence():
    from core.config import ROAD_CORRIDOR_STALENESS_SECONDS_THRESHOLD
    from datetime import datetime, timedelta
    living_map = LivingMap()
    
    # Old point (stale)
    t1 = create_sample_telemetry("TRUCK_01", 17.0000, 78.0000)
    t1.timestamp = datetime.utcnow() - timedelta(seconds=ROAD_CORRIDOR_STALENESS_SECONDS_THRESHOLD + 10)
    living_map.update_vehicle(t1)
    
    # Fresh point
    t2 = create_sample_telemetry("TRUCK_01", 17.0010, 78.0000)
    living_map.update_vehicle(t2)
    
    corridors = living_map.get_road_corridors()
    assert len(corridors) == 2
    assert corridors[0].is_stale is True
    assert corridors[1].is_stale is False
    assert corridors[1].confidence == 1.0

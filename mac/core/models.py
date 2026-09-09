from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class SimulatorConditions(BaseModel):
    visibility: str = "CLEAR" # CLEAR, FOG
    road: str = "DRY" # DRY, WET
    obstacle: str = "NONE" # NONE, PEDESTRIAN, OBSTACLE

class Alert(BaseModel):
    timestamp: datetime
    type: str
    message: str
    vehicle_id: Optional[str] = None

class GovernorDecision(BaseModel):
    state: str
    recommended_speed_kmh: float
    visibility_limit_kmh: float
    road_condition_limit_kmh: float
    final_speed_limit_kmh: float
    reason: str
    timestamp: datetime

class Position(BaseModel):
    latitude: float
    longitude: float
    altitude: Optional[float] = None

    @field_validator('latitude')
    def valid_latitude(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError('Latitude must be between -90 and 90')
        return v

    @field_validator('longitude')
    def valid_longitude(cls, v):
        if not (-180 <= v <= 180):
            raise ValueError('Longitude must be between -180 and 180')
        return v

class RoadCorridorPoint(Position):
    last_observed: datetime
    confidence: float
    is_stale: bool = False

class SARMetadata(BaseModel):
    product_id: str
    acquisition_time: datetime
    polarization: str
    bbox: tuple[float, float, float, float]
    source: str

class CandidateRoadSegment(BaseModel):
    route_id: str
    path_coordinates: List[Position]
    source: str
    confidence: float
    status: str
    last_observed: Optional[datetime] = None
    nearest_vehicle_ids: List[str] = []

class Motion(BaseModel):
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None

    @field_validator('speed_kmh')
    def valid_speed(cls, v):
        if v is not None and v < 0:
            raise ValueError('Speed cannot be negative')
        return v

class VehicleSensors(BaseModel):
    # TODO: populate from ESP32 radar telemetry
    radar_distance_m: Optional[float] = None
    
    # TODO: populate from ESP32 LDR telemetry
    visibility_adc: Optional[int] = None
    visibility_m: Optional[float] = None
    
    # TODO: populate from MPU6050
    acceleration_x: Optional[float] = None
    acceleration_y: Optional[float] = None
    acceleration_z: Optional[float] = None
    gyro_x: Optional[float] = None
    gyro_y: Optional[float] = None
    gyro_z: Optional[float] = None
    
    # TODO: populate from BMP280
    barometric_altitude_m: Optional[float] = None
    
    # TODO: populate from ENCODER
    wheel_distance_m: Optional[float] = None
    wheel_speed_kmh: Optional[float] = None

class State(BaseModel):
    brake_active: Optional[bool] = None
    obstacle_detected: Optional[bool] = None

class Metadata(BaseModel):
    position_source: str = "UNKNOWN"
    sensor_source: str = "UNKNOWN"
    gps_accuracy_m: Optional[float] = None
    confidence: str = "UNKNOWN"
    original_position: Optional[Position] = None
    
    @field_validator('gps_accuracy_m')
    def valid_accuracy(cls, v):
        if v is not None and v < 0:
            raise ValueError('Accuracy cannot be negative')
        return v

class VehicleTelemetry(BaseModel):
    vehicle_id: str
    timestamp: datetime
    
    position: Position
    motion: Motion
    vehicle_sensors: VehicleSensors = Field(default_factory=VehicleSensors)
    state: State = Field(default_factory=State)
    metadata: Metadata = Field(default_factory=Metadata)

    @field_validator('vehicle_id')
    def valid_vehicle_id(cls, v):
        if not v.strip():
            raise ValueError('Vehicle ID cannot be empty')
        return v

class Destination(BaseModel):
    name: str
    position: Position

class NearbyVehicle(BaseModel):
    vehicle_id: str
    distance_m: float
    bearing_deg: float
    relative_direction: str
    speed_kmh: Optional[float]
    heading_deg: Optional[float]


class SafetyAlert(BaseModel):
    alert_type: str
    severity: str # CLEAR, CAUTION, WARNING, CRITICAL
    distance_m: Optional[float] = None
    message: str
    source: str
    timestamp: datetime
    active: bool

class SafetyConstraint(BaseModel):
    type: str
    limit_kmh: float
    reason: str

class SafetyDecision(BaseModel):
    permitted_speed_kmh: float
    active_alert: Optional[SafetyAlert] = None
    alert_severity: str
    reason: str
    constraints: List[str]

class NavigationState(BaseModel):

    current_vehicle: Optional[str]
    current_position: Optional[Position]
    heading: Optional[float]
    speed: Optional[float]
    nearby_vehicles: List[NearbyVehicle]
    active_route: Optional[CandidateRoadSegment]
    route_source: Optional[str]
    destination: Optional[Destination]
    distance_to_destination_m: Optional[float]
    next_maneuver: Optional[str]
    maneuver_distance_m: Optional[float]
    maneuver_direction: Optional[str]
    camera_state: str
    governor: str
    visibility: str
    radar: str
    living_corridor_active: bool
    safety_decision: Optional[SafetyDecision] = None
    data_sources: dict
    projection_mode: str = "REAL_PHONE_GPS"
    road_type: Optional[str] = None
    gradient_percent: Optional[float] = None

class VirtualMineRoute(BaseModel):
    route_id: str
    name: str
    path_coordinates: List[Position]
    road_type: str
    gradient_percent: float

class VirtualVehicleState(BaseModel):
    vehicle_id: str
    raw_position: Position
    virtual_position: Position
    route_id: str
    route_progress_m: float
    virtual_heading_deg: float
    virtual_speed_kmh: float


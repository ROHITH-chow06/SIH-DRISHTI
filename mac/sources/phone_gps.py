from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from core.models import VehicleTelemetry, Position, Motion, Metadata, VehicleSensors, State
from core.config import get_gps_confidence

class PhoneGPSData(BaseModel):
    """
    Incoming raw data from the phone's HTML5 geolocation.
    """
    vehicle_id: str
    latitude: float
    longitude: float
    altitude: Optional[float] = None
    accuracy_m: Optional[float] = None
    speed_kmh: Optional[float] = None
    heading_deg: Optional[float] = None
    timestamp: datetime

def process_phone_gps(data: PhoneGPSData) -> VehicleTelemetry:
    """
    Converts raw phone GPS data into the standard VehicleTelemetry model.
    """
    confidence = get_gps_confidence(data.accuracy_m)
    
    return VehicleTelemetry(
        vehicle_id=data.vehicle_id,
        timestamp=data.timestamp,
        position=Position(
            latitude=data.latitude,
            longitude=data.longitude,
            altitude=data.altitude
        ),
        motion=Motion(
            speed_kmh=data.speed_kmh,
            heading_deg=data.heading_deg
        ),
        vehicle_sensors=VehicleSensors(), # Empty/None for now
        state=State(),                    # Empty/None for now
        metadata=Metadata(
            position_source="PHONE_GPS",
            sensor_source="UNAVAILABLE",
            gps_accuracy_m=data.accuracy_m,
            confidence=confidence
        )
    )

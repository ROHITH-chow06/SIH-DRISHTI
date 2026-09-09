from datetime import datetime
from typing import Optional
from core.models import VehicleTelemetry, Position, Motion, Metadata, VehicleSensors, State
from core.data_source import DataSource

class SimulationDataSource(DataSource):
    """
    Simulation source to test the data architecture before hardware is available.
    """
    def __init__(self, vehicle_id: str = "SIM_TRUCK_01"):
        self.vehicle_id = vehicle_id
        
    def get_latest_telemetry(self) -> Optional[VehicleTelemetry]:
        return VehicleTelemetry(
            vehicle_id=self.vehicle_id,
            timestamp=datetime.utcnow(),
            position=Position(
                latitude=17.3850,
                longitude=78.4867,
                altitude=540.2
            ),
            motion=Motion(
                speed_kmh=15.0,
                heading_deg=90.0
            ),
            vehicle_sensors=VehicleSensors(), # Empty
            state=State(),                    # Empty
            metadata=Metadata(
                position_source="SIMULATION",
                sensor_source="SIMULATION",
                gps_accuracy_m=1.0,
                confidence="HIGH"
            )
        )

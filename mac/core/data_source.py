from abc import ABC, abstractmethod
from typing import Optional
from core.models import VehicleTelemetry

class DataSource(ABC):
    """
    Base class for all DRISHTI telemetry data sources.
    This ensures a common interface whether the data comes from
    a phone, RTK GPS, ESP32 sensors, or simulation.
    """
    
    @abstractmethod
    def get_latest_telemetry(self) -> Optional[VehicleTelemetry]:
        """
        Returns the latest available telemetry or None if not available.
        """
        pass

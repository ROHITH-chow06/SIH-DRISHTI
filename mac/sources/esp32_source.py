from typing import Optional
from core.models import VehicleTelemetry
from core.data_source import DataSource

class ESP32DataSource(DataSource):
    """
    Interface for future ESP32 serial/network data source.
    This will eventually connect to the physical prototype hardware
    and parse the incoming packets (e.g. over MQTT or Serial).
    """
    def __init__(self, port: str = "COM1"):
        self.port = port
        # TODO: initialize serial/network connection here
        
    def get_latest_telemetry(self) -> Optional[VehicleTelemetry]:
        """
        Reads the latest packet from the ESP32 and returns a populated 
        VehicleTelemetry object. Returns None if no new valid data.
        """
        # TODO: read hardware data, parse it, and populate the telemetry
        return None

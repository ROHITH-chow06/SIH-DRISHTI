import os
from typing import Optional

# Server configuration
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", 8000))

# Vehicle configuration
DEFAULT_VEHICLE_ID = os.getenv("DEFAULT_VEHICLE_ID", "TRUCK_01")

# GPS Configuration
GPS_UPDATE_INTERVAL_MS = int(os.getenv("GPS_UPDATE_INTERVAL", 1000))

# Navigation Configuration
NAVIGATION_RADIUS_M = float(os.getenv("NAVIGATION_RADIUS_M", 500.0))
NAVIGATION_CONTEXT_EXIT_RADIUS_M = float(os.getenv("NAVIGATION_CONTEXT_EXIT_RADIUS_M", 550.0))

# Virtual Mine Configuration
VIRTUAL_MOVEMENT_THRESHOLD_M = float(os.getenv("VIRTUAL_MOVEMENT_THRESHOLD_M", 2.0))
VIRTUAL_MODE_DEFAULT = os.getenv("VIRTUAL_MODE_DEFAULT", "true").lower() == "true"

# GPS Confidence Thresholds in meters
GPS_CONFIDENCE_HIGH_THRESHOLD_M = 5.0
GPS_CONFIDENCE_MEDIUM_THRESHOLD_M = 15.0

# Road Corridor Distance Threshold in meters
ROAD_CORRIDOR_MIN_DISTANCE_M = float(os.getenv("ROAD_CORRIDOR_MIN_DISTANCE_M", 5.0))
# Road Corridor Staleness Threshold in seconds
ROAD_CORRIDOR_STALENESS_SECONDS_THRESHOLD = int(os.getenv("ROAD_CORRIDOR_STALENESS_SECONDS_THRESHOLD", 300))

# Distance threshold for meaningful route observations (prevent stationary confidence spiking)
ROAD_ROUTE_MIN_OBSERVATION_DISTANCE_M = float(os.getenv("ROAD_ROUTE_MIN_OBSERVATION_DISTANCE_M", 5.0))

# SAR Configuration (NMDC Bailadila Deposit-5)
SAR_SITE_NAME = os.getenv("SAR_SITE_NAME", "NMDC Bailadila Deposit-5")
# BBOX: (min_lon, min_lat, max_lon, max_lat)
SAR_BBOX = (
    float(os.getenv("SAR_BBOX_MIN_LON", 81.1782861)),
    float(os.getenv("SAR_BBOX_MIN_LAT", 18.6668167)),
    float(os.getenv("SAR_BBOX_MAX_LON", 81.2088583)),
    float(os.getenv("SAR_BBOX_MAX_LAT", 18.6973278))
)
SAR_ANCHOR_LAT = float(os.getenv("SAR_ANCHOR_LAT", 18.682072))
SAR_ANCHOR_LON = float(os.getenv("SAR_ANCHOR_LON", 81.193572))

# GPS Display Mode: "real" or "demo_anchored"
GPS_DISPLAY_MODE = os.getenv("GPS_DISPLAY_MODE", "demo_anchored")

def get_gps_confidence(accuracy_m: Optional[float]) -> str:
    if accuracy_m is None or accuracy_m < 0:
        return "UNKNOWN"
    if accuracy_m <= GPS_CONFIDENCE_HIGH_THRESHOLD_M:
        return "HIGH"
    if accuracy_m <= GPS_CONFIDENCE_MEDIUM_THRESHOLD_M:
        return "MEDIUM"
    return "LOW"

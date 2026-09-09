import math
from typing import Dict, List, Optional
from core.models import Position, VehicleTelemetry, VirtualMineRoute, VirtualVehicleState
from core.config import VIRTUAL_MOVEMENT_THRESHOLD_M

def _haversine(p1: Position, p2: Position) -> float:
    R = 6371000  # meters
    phi1 = math.radians(p1.latitude)
    phi2 = math.radians(p2.latitude)
    delta_phi = math.radians(p2.latitude - p1.latitude)
    delta_lambda = math.radians(p2.longitude - p1.longitude)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def _calculate_bearing(p1: Position, p2: Position) -> float:
    lat1 = math.radians(p1.latitude)
    lon1 = math.radians(p1.longitude)
    lat2 = math.radians(p2.latitude)
    lon2 = math.radians(p2.longitude)
    dlon = lon2 - lon1
    y = math.sin(dlon) * math.cos(lat2)
    x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
    brng = math.atan2(y, x)
    return (math.degrees(brng) + 360) % 360

def _interpolate_along_path(path: List[Position], progress_m: float) -> tuple[Position, float]:
    """Returns interpolated Position and the heading at that segment."""
    if not path:
        return Position(latitude=0, longitude=0), 0.0
    if len(path) == 1:
        return path[0], 0.0

    accumulated = 0.0
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i+1]
        dist = _haversine(p1, p2)
        if accumulated + dist >= progress_m:
            # We are on this segment
            overshoot = progress_m - accumulated
            fraction = overshoot / dist if dist > 0 else 0
            
            lat = p1.latitude + (p2.latitude - p1.latitude) * fraction
            lon = p1.longitude + (p2.longitude - p1.longitude) * fraction
            
            heading = _calculate_bearing(p1, p2)
            return Position(latitude=lat, longitude=lon), heading
            
        accumulated += dist

    # If we exceed the total length, just return the last point and heading of the last segment
    last_heading = _calculate_bearing(path[-2], path[-1])
    return path[-1], last_heading

def _closest_point_on_path(path: List[Position], pos: Position) -> float:
    """Finds the closest point on a path to a given position and returns the progress_m to that point."""
    if not path or len(path) < 2:
        return 0.0
        
    best_progress = 0.0
    min_dist = float('inf')
    accumulated = 0.0
    
    for i in range(len(path) - 1):
        p1 = path[i]
        p2 = path[i+1]
        segment_dist = _haversine(p1, p2)
        
        # We can do a brute-force sampling of the segment for simplicity
        samples = max(2, int(segment_dist))
        for j in range(samples + 1):
            fraction = j / samples
            sample_lat = p1.latitude + (p2.latitude - p1.latitude) * fraction
            sample_lon = p1.longitude + (p2.longitude - p1.longitude) * fraction
            sample_pos = Position(latitude=sample_lat, longitude=sample_lon)
            
            dist_to_sample = _haversine(pos, sample_pos)
            if dist_to_sample < min_dist:
                min_dist = dist_to_sample
                best_progress = accumulated + (segment_dist * fraction)
                
        accumulated += segment_dist
        
    return best_progress

class VirtualMineEnvironment:
    def __init__(self):
        # Using authentic route coordinates derived from SAR data to perfectly align with map terrain
        self.routes = {
            "LOADING AREA": VirtualMineRoute(
                route_id="LOADING AREA",
                name="LOADING AREA",
                path_coordinates=[
                    Position(latitude=18.682072, longitude=81.193572),
                    Position(latitude=18.682126, longitude=81.193572),
                    Position(latitude=18.682216, longitude=81.193482),
                    Position(latitude=18.682306, longitude=81.1934),
                    Position(latitude=18.68245, longitude=81.1935),
                    Position(latitude=18.6826, longitude=81.193572),
                    Position(latitude=18.683, longitude=81.1945),
                    Position(latitude=18.6845, longitude=81.195),
                    Position(latitude=18.686, longitude=81.1955),
                    Position(latitude=18.6875, longitude=81.1965),
                    Position(latitude=18.6885, longitude=81.1975),
                    Position(latitude=18.69, longitude=81.1985),
                    Position(latitude=18.692, longitude=81.1995),
                    Position(latitude=18.694, longitude=81.201),
                    Position(latitude=18.696, longitude=81.203)
                ],
                road_type="HAUL",
                gradient_percent=2.0
            ),
            "FACE ACCESS": VirtualMineRoute(
                route_id="FACE ACCESS",
                name="FACE ACCESS",
                path_coordinates=[
                    Position(latitude=18.682072, longitude=81.191572),
                    Position(latitude=18.681988, longitude=81.191597),
                    Position(latitude=18.681904, longitude=81.19167),
                    Position(latitude=18.68182, longitude=81.19179),
                    Position(latitude=18.681736, longitude=81.191954),
                    Position(latitude=18.681652, longitude=81.192158),
                    Position(latitude=18.681568, longitude=81.192396),
                    Position(latitude=18.681484, longitude=81.192664),
                    Position(latitude=18.681401, longitude=81.192954),
                    Position(latitude=18.681317, longitude=81.193259),
                    Position(latitude=18.681233, longitude=81.193572),
                    Position(latitude=18.681149, longitude=81.193885),
                    Position(latitude=18.681065, longitude=81.19419),
                    Position(latitude=18.680981, longitude=81.19448),
                    Position(latitude=18.680897, longitude=81.194748),
                    Position(latitude=18.680813, longitude=81.194986),
                    Position(latitude=18.680729, longitude=81.19519),
                    Position(latitude=18.680645, longitude=81.195354),
                    Position(latitude=18.680561, longitude=81.195474),
                    Position(latitude=18.680477, longitude=81.195547),
                    Position(latitude=18.680393, longitude=81.195572),
                    Position(latitude=18.680309, longitude=81.195547),
                    Position(latitude=18.680225, longitude=81.195474),
                    Position(latitude=18.680142, longitude=81.195354),
                    Position(latitude=18.680058, longitude=81.19519),
                    Position(latitude=18.679974, longitude=81.194986),
                    Position(latitude=18.67989, longitude=81.194748),
                    Position(latitude=18.679806, longitude=81.19448),
                    Position(latitude=18.679722, longitude=81.19419),
                    Position(latitude=18.679638, longitude=81.193885),
                    Position(latitude=18.679554, longitude=81.193572),
                    Position(latitude=18.67947, longitude=81.193259),
                    Position(latitude=18.679386, longitude=81.192954),
                    Position(latitude=18.679302, longitude=81.192664),
                    Position(latitude=18.679218, longitude=81.192396),
                    Position(latitude=18.679134, longitude=81.192158),
                    Position(latitude=18.67905, longitude=81.191954),
                    Position(latitude=18.678966, longitude=81.19179),
                    Position(latitude=18.678883, longitude=81.19167),
                    Position(latitude=18.678799, longitude=81.191597),
                    Position(latitude=18.678715, longitude=81.191572),
                    Position(latitude=18.678631, longitude=81.191597),
                    Position(latitude=18.678547, longitude=81.19167),
                    Position(latitude=18.678463, longitude=81.19179),
                    Position(latitude=18.678379, longitude=81.191954),
                    Position(latitude=18.678295, longitude=81.192158),
                    Position(latitude=18.678211, longitude=81.192396),
                    Position(latitude=18.678127, longitude=81.192664),
                    Position(latitude=18.678043, longitude=81.192954),
                    Position(latitude=18.677959, longitude=81.193259),
                    Position(latitude=18.677875, longitude=81.193572),
                    Position(latitude=18.677791, longitude=81.193885),
                    Position(latitude=18.677707, longitude=81.19419),
                    Position(latitude=18.677624, longitude=81.19448),
                    Position(latitude=18.67754, longitude=81.194748),
                    Position(latitude=18.677456, longitude=81.194986),
                    Position(latitude=18.677372, longitude=81.19519),
                    Position(latitude=18.677288, longitude=81.195354),
                    Position(latitude=18.677204, longitude=81.195474),
                    Position(latitude=18.67712, longitude=81.195547),
                    Position(latitude=18.677036, longitude=81.195572),
                    Position(latitude=18.676952, longitude=81.195547),
                    Position(latitude=18.676868, longitude=81.195474),
                    Position(latitude=18.676784, longitude=81.195354),
                    Position(latitude=18.6767, longitude=81.19519),
                    Position(latitude=18.676616, longitude=81.194986),
                    Position(latitude=18.676532, longitude=81.194748),
                    Position(latitude=18.676448, longitude=81.19448),
                    Position(latitude=18.676365, longitude=81.19419),
                    Position(latitude=18.676281, longitude=81.193885),
                    Position(latitude=18.676197, longitude=81.193572),
                    Position(latitude=18.676113, longitude=81.193259),
                    Position(latitude=18.676029, longitude=81.192954),
                    Position(latitude=18.675945, longitude=81.192664),
                    Position(latitude=18.675861, longitude=81.192396),
                    Position(latitude=18.675777, longitude=81.192158),
                    Position(latitude=18.675693, longitude=81.191954),
                    Position(latitude=18.675609, longitude=81.19179),
                    Position(latitude=18.675525, longitude=81.19167),
                    Position(latitude=18.675441, longitude=81.191597),
                    Position(latitude=18.675357, longitude=81.191572),
                    Position(latitude=18.675273, longitude=81.191597),
                    Position(latitude=18.675189, longitude=81.19167),
                    Position(latitude=18.675106, longitude=81.19179),
                    Position(latitude=18.675022, longitude=81.191954),
                    Position(latitude=18.674938, longitude=81.192158),
                    Position(latitude=18.674854, longitude=81.192396),
                    Position(latitude=18.67477, longitude=81.192664),
                    Position(latitude=18.674686, longitude=81.192954),
                    Position(latitude=18.674602, longitude=81.193259),
                    Position(latitude=18.674518, longitude=81.193572),
                    Position(latitude=18.674434, longitude=81.193885),
                    Position(latitude=18.67435, longitude=81.19419),
                    Position(latitude=18.674266, longitude=81.19448),
                    Position(latitude=18.674182, longitude=81.194748),
                    Position(latitude=18.674098, longitude=81.194986),
                    Position(latitude=18.674014, longitude=81.19519),
                    Position(latitude=18.67393, longitude=81.195354),
                    Position(latitude=18.673847, longitude=81.195474),
                    Position(latitude=18.673763, longitude=81.195547),
                    Position(latitude=18.673679, longitude=81.195572),
                    Position(latitude=18.673595, longitude=81.195547),
                    Position(latitude=18.673511, longitude=81.195474),
                    Position(latitude=18.673427, longitude=81.195354),
                    Position(latitude=18.673343, longitude=81.19519),
                    Position(latitude=18.673259, longitude=81.194986),
                    Position(latitude=18.673175, longitude=81.194748),
                    Position(latitude=18.673091, longitude=81.19448),
                    Position(latitude=18.673007, longitude=81.19419),
                    Position(latitude=18.672923, longitude=81.193885),
                    Position(latitude=18.672839, longitude=81.193572),
                    Position(latitude=18.672755, longitude=81.193259),
                    Position(latitude=18.672671, longitude=81.192954),
                    Position(latitude=18.672588, longitude=81.192664),
                    Position(latitude=18.672504, longitude=81.192396),
                    Position(latitude=18.67242, longitude=81.192158),
                    Position(latitude=18.672336, longitude=81.191954),
                    Position(latitude=18.672252, longitude=81.19179),
                    Position(latitude=18.672168, longitude=81.19167),
                    Position(latitude=18.672084, longitude=81.191597)
                ],
                road_type="GHAT",
                gradient_percent=8.5
            )
        }

    def get_route(self, route_id: str) -> Optional[VirtualMineRoute]:
        return self.routes.get(route_id)

class VirtualVehicleProjector:
    def __init__(self, environment: VirtualMineEnvironment):
        self.environment = environment
        self.virtual_states: Dict[str, VirtualVehicleState] = {}
        self.last_raw_positions: Dict[str, Position] = {}
        self.movement_threshold = VIRTUAL_MOVEMENT_THRESHOLD_M

    def update(self, vehicle_id: str, telemetry: VehicleTelemetry, active_destination: Optional[str]) -> Optional[VirtualVehicleState]:
        current_raw = telemetry.position
        route_id = active_destination if active_destination and active_destination in self.environment.routes else "LOADING AREA"
        route = self.environment.get_route(route_id)
        if not route:
            return None

        if vehicle_id not in self.virtual_states:
            # Initialize at start of the route
            pos, heading = _interpolate_along_path(route.path_coordinates, 0)
            self.virtual_states[vehicle_id] = VirtualVehicleState(
                vehicle_id=vehicle_id,
                raw_position=current_raw,
                virtual_position=pos,
                route_id=route_id,
                route_progress_m=0.0,
                virtual_heading_deg=heading,
                virtual_speed_kmh=telemetry.motion.speed_kmh or 0.0
            )
            self.last_raw_positions[vehicle_id] = current_raw
            return self.virtual_states[vehicle_id]

        state = self.virtual_states[vehicle_id]
        last_raw = self.last_raw_positions.get(vehicle_id, current_raw)
        
        # Handle route change
        if state.route_id != route_id:
            # Find closest progress on new route
            new_progress = _closest_point_on_path(route.path_coordinates, state.virtual_position)
            state.route_id = route_id
            state.route_progress_m = new_progress

        # Accumulate physical distance
        delta_m = _haversine(last_raw, current_raw)
        if delta_m >= self.movement_threshold:
            state.route_progress_m += delta_m
            self.last_raw_positions[vehicle_id] = current_raw
        
        # Interpolate
        pos, heading = _interpolate_along_path(route.path_coordinates, state.route_progress_m)
        
        # Detect if we've arrived
        total_length = sum([_haversine(route.path_coordinates[i], route.path_coordinates[i+1]) for i in range(len(route.path_coordinates)-1)])
        if state.route_progress_m >= total_length:
            state.route_progress_m = total_length # Cap it

        state.raw_position = current_raw
        state.virtual_position = pos
        state.virtual_heading_deg = heading
        state.virtual_speed_kmh = telemetry.motion.speed_kmh or 0.0

        return state

    def reset_vehicle(self, vehicle_id: str):
        if vehicle_id in self.virtual_states:
            del self.virtual_states[vehicle_id]
        if vehicle_id in self.last_raw_positions:
            del self.last_raw_positions[vehicle_id]

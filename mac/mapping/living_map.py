import math
from datetime import datetime, timezone
from typing import Dict, List, Optional
from threading import Lock
from core.models import VehicleTelemetry, Position, RoadCorridorPoint, CandidateRoadSegment
from core.config import ROAD_CORRIDOR_MIN_DISTANCE_M, ROAD_CORRIDOR_STALENESS_SECONDS_THRESHOLD, ROAD_ROUTE_MIN_OBSERVATION_DISTANCE_M
from mapping.route_source import DemoRouteSource

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

class LivingMap:
    """
    LivingMap acts as the central spatial repository and representation of vehicle traces.
    Consumes VehicleTelemetry objects from the telemetry layer.
    """
    def __init__(self, on_alert=None):
        self.on_alert = on_alert
        # Maps vehicle_id -> list of VehicleTelemetry objects representing trace history
        self._vehicle_traces: Dict[str, List[VehicleTelemetry]] = {}
        # Unified road corridor accumulated from all vehicle traces
        self._accumulated_road_corridor: List[RoadCorridorPoint] = []
        
        # Candidate Routes
        self._candidate_routes: Dict[str, CandidateRoadSegment] = {}
        self._load_candidate_routes()
        
        # Track meaningful route observations per vehicle
        self._last_meaningful_observation_pos: Dict[str, Position] = {}
        
        self._lock = Lock()

    def _load_candidate_routes(self):
        source = DemoRouteSource()
        for r in source.load_routes():
            self._candidate_routes[r.route_id] = r

    def update_vehicle(self, telemetry: VehicleTelemetry) -> None:
        """
        Updates the spatial state for a vehicle by appending the latest telemetry.
        """
        vehicle_id = telemetry.vehicle_id
        if vehicle_id not in self._vehicle_traces:
            self._vehicle_traces[vehicle_id] = []
        self._vehicle_traces[vehicle_id].append(telemetry)
        
        # Process route observation
        with self._lock:
            self._process_candidate_route_observation(telemetry)
        
        # Accumulate road corridor
        pos = telemetry.position
        should_add = True
        
        # Only check against the last point to keep things fast, 
        # or check all points if the corridor is small. For simplicity, check the last point.
        if self._accumulated_road_corridor:
            last_p = self._accumulated_road_corridor[-1]
            dist = haversine_distance_m(pos.latitude, pos.longitude, last_p.latitude, last_p.longitude)
            if dist < ROAD_CORRIDOR_MIN_DISTANCE_M:
                should_add = False
                # Update existing point confidence and staleness
                last_p.last_observed = max(last_p.last_observed, telemetry.timestamp)
                last_p.confidence = min(1.0, last_p.confidence + 0.1)
        
        if should_add:
            new_pt = RoadCorridorPoint(
                latitude=pos.latitude,
                longitude=pos.longitude,
                altitude=pos.altitude,
                last_observed=telemetry.timestamp,
                confidence=1.0,
                is_stale=False
            )
            self._accumulated_road_corridor.append(new_pt)

    def get_current_positions(self) -> Dict[str, Optional[Position]]:
        """
        Returns a dictionary mapping vehicle_id to its latest known position.
        """
        positions = {}
        for vehicle_id, trace in self._vehicle_traces.items():
            if trace:
                positions[vehicle_id] = trace[-1].position
            else:
                positions[vehicle_id] = None
        return positions

    def get_current_telemetry(self, vehicle_id: str) -> Optional[VehicleTelemetry]:
        """
        Returns the latest full telemetry object for a given vehicle.
        """
        trace = self._vehicle_traces.get(vehicle_id)
        if trace:
            return trace[-1]
        return None

    def get_vehicle_trace(self, vehicle_id: str) -> List[Position]:
        """
        Returns the historical list of positions (trace) for a given vehicle.
        """
        trace = self._vehicle_traces.get(vehicle_id, [])
        return [t.position for t in trace]

    def get_vehicle_telemetry_history(self, vehicle_id: str) -> List[VehicleTelemetry]:
        """
        Returns the full historical list of telemetry points for a given vehicle.
        """
        return self._vehicle_traces.get(vehicle_id, [])

    def get_point_count(self, vehicle_id: str) -> int:
        """
        Returns the number of received telemetry points for a vehicle.
        """
        return len(self._vehicle_traces.get(vehicle_id, []))

    def get_tracked_vehicles(self) -> List[str]:
        """
        Returns a list of all vehicle IDs currently tracked on the map.
        """
        return list(self._vehicle_traces.keys())

    def _haversine_distance_m(self, p1: Position, p2: Position) -> float:
        return haversine_distance_m(p1.latitude, p1.longitude, p2.latitude, p2.longitude)

    def _process_candidate_route_observation(self, telemetry: VehicleTelemetry):
        pos = telemetry.position
        vid = telemetry.vehicle_id
        
        # Check if enough distance has passed since last meaningful observation
        last_obs = self._last_meaningful_observation_pos.get(vid)
        if last_obs is not None:
            dist = self._haversine_distance_m(last_obs, pos)
            if dist < ROAD_ROUTE_MIN_OBSERVATION_DISTANCE_M:
                return # Not enough movement
                
        # Find nearest route within 25m
        nearest_route = None
        min_dist = 25.0
        
        for route in self._candidate_routes.values():
            for rp in route.path_coordinates:
                d = self._haversine_distance_m(pos, rp)
                if d < min_dist:
                    min_dist = d
                    nearest_route = route
                    
        if nearest_route:
            # We made a meaningful observation of this route
            self._last_meaningful_observation_pos[vid] = pos
            nearest_route.last_observed = telemetry.timestamp
            
            if nearest_route.status != "VALIDATED" and self.on_alert:
                self.on_alert("INFO", f"Vehicle route validated", vid)
                
            nearest_route.status = "VALIDATED"
            nearest_route.confidence = min(1.0, nearest_route.confidence + 0.1)
            if vid not in nearest_route.nearest_vehicle_ids:
                nearest_route.nearest_vehicle_ids.append(vid)

    def get_candidate_routes(self) -> List[CandidateRoadSegment]:
        with self._lock:
            # Update staleness
            now = datetime.utcnow()
            for r in self._candidate_routes.values():
                if r.status == "VALIDATED" and r.last_observed:
                    if (now - r.last_observed.replace(tzinfo=None)).total_seconds() > ROAD_CORRIDOR_STALENESS_SECONDS_THRESHOLD:
                        r.status = "STALE"
            return list(self._candidate_routes.values())

    def get_road_corridors(self) -> List[RoadCorridorPoint]:
        """
        Returns the accumulated road corridor network derived from vehicle GPS traces.
        Computes staleness dynamically before returning.
        """
        now = datetime.utcnow()
        for pt in self._accumulated_road_corridor:
            # Handle tz-aware timestamps if necessary
            current_time = now.replace(tzinfo=timezone.utc) if pt.last_observed.tzinfo else now
            delta = (current_time - pt.last_observed).total_seconds()
            pt.is_stale = delta > ROAD_CORRIDOR_STALENESS_SECONDS_THRESHOLD
        return self._accumulated_road_corridor

    # =========================================================================
    # Extension Points for Future Map Layers
    # =========================================================================

    def update_drone_layer(self, drone_data: dict) -> None:
        """
        TODO (Future): Extension point for incorporating drone aerial telemetry / imagery layer.
        """
        pass

    def update_sar_validation(self, sar_data: dict) -> None:
        """
        TODO (Future): Extension point for Synthetic Aperture Radar (SAR) validation layers.
        """
        pass

    def update_road_corridors(self, corridor_data: dict) -> None:
        """
        TODO (Future): Extension point for static/dynamic road corridor map constraints.
        """
        pass

    def update_radar_obstacles(self, obstacle_data: dict) -> None:
        """
        TODO (Future): Extension point for accumulating radar obstacle detections on the map.
        """
        pass

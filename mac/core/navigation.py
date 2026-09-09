import math
from typing import List, Optional, Dict
from core.models import (
    VehicleTelemetry, Position, CandidateRoadSegment, 
    Destination, NearbyVehicle, NavigationState
)
from mapping.living_map import LivingMap
from core.safety import DualConstraintGovernor

# Mock Destinations for Demo
DESTINATIONS = [
    Destination(name="MINE ENTRANCE", position=Position(latitude=18.6670, longitude=81.1800)),
    Destination(name="LOADING AREA", position=Position(latitude=18.6960, longitude=81.2030)),
    Destination(name="DUMP AREA", position=Position(latitude=18.6700, longitude=81.1850)),
    Destination(name="FACE ACCESS", position=Position(latitude=18.6815, longitude=81.1970)),
]

from core.config import NAVIGATION_RADIUS_M, NAVIGATION_CONTEXT_EXIT_RADIUS_M, VIRTUAL_MODE_DEFAULT
from core.virtual_mine import VirtualMineEnvironment, VirtualVehicleProjector

class NavigationEngine:
    def __init__(self, living_map: LivingMap):
        self.living_map = living_map
        self.current_vehicle_id: Optional[str] = None
        self.active_destination: Optional[Destination] = None
        self.active_route: Optional[CandidateRoadSegment] = None
        self.navigation_radius_m: float = NAVIGATION_RADIUS_M
        self.context_vehicles = set()
        
        self.virtual_mode = VIRTUAL_MODE_DEFAULT
        self.virtual_env = VirtualMineEnvironment()
        self.projector = VirtualVehicleProjector(self.virtual_env)
        
    def reset_virtual_state(self, vehicle_id: Optional[str] = None):
        if vehicle_id:
            self.projector.reset_vehicle(vehicle_id)
        elif self.current_vehicle_id:
            self.projector.reset_vehicle(self.current_vehicle_id)

    def set_current_vehicle(self, vehicle_id: str):
        self.current_vehicle_id = vehicle_id

    def set_destination(self, dest_name: str):
        for d in DESTINATIONS:
            if d.name == dest_name:
                self.active_destination = d
                self.recalculate_route()
                return
        self.active_destination = None
        self.active_route = None

    def recalculate_route(self):
        if not self.active_destination or not self.current_vehicle_id:
            self.active_route = None
            return
            
        candidates = self.living_map.get_candidate_routes()
        if not candidates:
            self.active_route = None
            return
            
        # Scoring: We want VALIDATED, then CANDIDATE. We do not want STALE.
        # Prefer routes where the destination is close to one of the path points.
        best_route = None
        best_score = float('-inf')
        
        for route in candidates:
            # Demerit if stale
            if route.status == "STALE":
                continue
                
            score = 0
            if route.status == "VALIDATED":
                score += 1000
                
            score += route.confidence * 100
            
            # Distance to destination penalty
            if route.path_coordinates:
                # Find min distance from route to destination
                min_dist_to_dest = min(
                    self._haversine(pt, self.active_destination.position)
                    for pt in route.path_coordinates
                )
                score -= min_dist_to_dest
                
            if score > best_score:
                best_score = score
                best_route = route
                
        self.active_route = best_route

    def _haversine(self, p1: Position, p2: Position) -> float:
        R = 6371000  # radius of Earth in meters
        phi1, phi2 = math.radians(p1.latitude), math.radians(p2.latitude)
        dphi = math.radians(p2.latitude - p1.latitude)
        dlambda = math.radians(p2.longitude - p1.longitude)
        
        a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2) * math.sin(dlambda/2)**2
        return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    def _calculate_bearing(self, p1: Position, p2: Position) -> float:
        lat1, lon1 = math.radians(p1.latitude), math.radians(p1.longitude)
        lat2, lon2 = math.radians(p2.latitude), math.radians(p2.longitude)
        
        dlon = lon2 - lon1
        x = math.sin(dlon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        
        initial_bearing = math.atan2(x, y)
        bearing = (math.degrees(initial_bearing) + 360) % 360
        return bearing

    def _get_relative_direction(self, bearing: float) -> str:
        dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
        idx = int((bearing + 22.5) / 45.0) % 8
        return dirs[idx]


    def _calculate_bearing(self, p1: Position, p2: Position) -> float:
        lat1, lon1 = math.radians(p1.latitude), math.radians(p1.longitude)
        lat2, lon2 = math.radians(p2.latitude), math.radians(p2.longitude)
        dlon = lon2 - lon1
        y = math.sin(dlon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dlon)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def _calculate_next_maneuver(self, current_pos: Position) -> tuple[Optional[str], Optional[float], Optional[str]]:
        if not self.active_route or len(self.active_route.path_coordinates) < 2:
            return None, None, None
            
        path = self.active_route.path_coordinates
        
        # 1. Find the closest point index to the vehicle
        closest_idx = 0
        min_dist = float('inf')
        for i, pt in enumerate(path):
            d = self._haversine(current_pos, pt)
            if d < min_dist:
                min_dist = d
                closest_idx = i
                
        # 2. Look ahead for turns
        # If we are near the end, there is no maneuver to make.
        if closest_idx >= len(path) - 2:
            return "FOLLOW ROUTE", None, "↑"
            
        accumulated_dist = 0.0
        current_bearing = self._calculate_bearing(path[closest_idx], path[closest_idx+1])
        
        for i in range(closest_idx + 1, len(path) - 1):
            seg_dist = self._haversine(path[i-1], path[i])
            accumulated_dist += seg_dist
            
            # Stop looking ahead if it's too far (e.g., 500 meters)
            if accumulated_dist > 500:
                break
                
            next_bearing = self._calculate_bearing(path[i], path[i+1])
            diff = (next_bearing - current_bearing + 180) % 360 - 180
            
            if abs(diff) > 20:
                # We found a turn
                dist = self._haversine(current_pos, path[i])
                
                # If the turn is very close, classify it
                if diff > 45:
                    return "RIGHT", round(dist), "→"
                elif diff > 20:
                    return "SLIGHT RIGHT", round(dist), "↗"
                elif diff < -45:
                    return "LEFT", round(dist), "←"
                elif diff < -20:
                    return "SLIGHT LEFT", round(dist), "↖"
                    
        return "FOLLOW ROUTE", None, "↑"

    def get_state(self, latest_telemetry_store: Dict[str, VehicleTelemetry], simulator_conditions) -> NavigationState:
        # Check route staleness to adapt
        if self.active_route:
            # Re-fetch the route from living map to check current status
            routes = self.living_map.get_candidate_routes()
            current_route = next((r for r in routes if r.route_id == self.active_route.route_id), None)
            if not current_route or current_route.status == "STALE":
                self.recalculate_route()

        curr_telemetry = latest_telemetry_store.get(self.current_vehicle_id) if self.current_vehicle_id else None
        
        nearby = []
        dist_to_dest = None
        
        new_context = set()
        
        road_type = None
        gradient_percent = None
        projection_mode = "REAL_PHONE_GPS"
        
        # Default destination for virtual mode if not set
        if self.virtual_mode and not self.active_destination:
            for d in DESTINATIONS:
                if d.name == "LOADING AREA":
                    self.set_destination("LOADING AREA")
                    break
        
        active_dest_name = self.active_destination.name if self.active_destination else None
        
        if curr_telemetry:
            if self.virtual_mode:
                v_state = self.projector.update(self.current_vehicle_id, curr_telemetry, active_dest_name)
                if v_state:
                    p1 = v_state.virtual_position
                    heading_deg = v_state.virtual_heading_deg
                    speed_kmh = v_state.virtual_speed_kmh
                    projection_mode = "DEMO_VIRTUAL_MINE"
                    
                    # Pull route metadata
                    v_route = self.virtual_env.get_route(v_state.route_id)
                    if v_route:
                        road_type = v_route.road_type
                        gradient_percent = v_route.gradient_percent
                        
                        # Mock the active route so it renders on the frontend map
                        self.active_route = CandidateRoadSegment(
                            route_id=v_route.route_id,
                            path_coordinates=v_route.path_coordinates,
                            source="DEMO VIRTUAL MINE",
                            confidence=100.0,
                            status="ACTIVE"
                        )
                        
                        if road_type == "GHAT":
                            # Subtle Ghat integration (just informative for now)
                            pass
                else:
                    p1 = curr_telemetry.position
                    heading_deg = curr_telemetry.motion.heading_deg
                    speed_kmh = curr_telemetry.motion.speed_kmh
            else:
                p1 = curr_telemetry.position
                heading_deg = curr_telemetry.motion.heading_deg
                speed_kmh = curr_telemetry.motion.speed_kmh
            
            # Nearby Vehicles
            for vid, tel in latest_telemetry_store.items():
                if vid == self.current_vehicle_id:
                    continue
                    
                if self.virtual_mode:
                    # other vehicles also get projected
                    ov_state = self.projector.update(vid, tel, active_dest_name)
                    if ov_state:
                        p2 = ov_state.virtual_position
                        o_heading = ov_state.virtual_heading_deg
                        o_speed = ov_state.virtual_speed_kmh
                    else:
                        p2 = tel.position
                        o_heading = tel.motion.heading_deg
                        o_speed = tel.motion.speed_kmh
                else:
                    p2 = tel.position
                    o_heading = tel.motion.heading_deg
                    o_speed = tel.motion.speed_kmh
                    
                dist = self._haversine(p1, p2)
                
                # Camera Hysteresis Logic
                if dist <= self.navigation_radius_m:
                    new_context.add(vid)
                elif vid in self.context_vehicles and dist <= NAVIGATION_CONTEXT_EXIT_RADIUS_M:
                    new_context.add(vid)
                
                # Strict Nearby Display Logic
                if dist <= self.navigation_radius_m:
                    bearing = self._calculate_bearing(p1, p2)
                    rel_dir = self._get_relative_direction(bearing)
                    nearby.append(NearbyVehicle(
                        vehicle_id=vid,
                        distance_m=round(dist, 1),
                        bearing_deg=round(bearing, 1),
                        relative_direction=rel_dir,
                        speed_kmh=o_speed,
                        heading_deg=o_heading
                    ))
            nearby.sort(key=lambda x: x.distance_m)
            
            self.context_vehicles = new_context
            
            if self.active_destination:
                dist_to_dest = self._haversine(p1, self.active_destination.position)

        # We need next_maneuver before safety so we know if there is a turn constraint
        next_maneuver, maneuver_distance_m, maneuver_direction = None, None, None
        if curr_telemetry:
            if dist_to_dest and dist_to_dest <= 50:
                next_maneuver = "ARRIVING AT " + (self.active_destination.name if self.active_destination else "DESTINATION")
                maneuver_distance_m = round(dist_to_dest, 0)
                maneuver_direction = "★"
            elif self.active_route:
                next_maneuver, maneuver_distance_m, maneuver_direction = self._calculate_next_maneuver(p1)
                
                if next_maneuver == "FOLLOW ROUTE" and dist_to_dest:
                    maneuver_distance_m = round(dist_to_dest, 0)
                    
        curr_speed = curr_telemetry.motion.speed_kmh if curr_telemetry and curr_telemetry.motion.speed_kmh else 0.0
        safety_decision = DualConstraintGovernor.calculate_safe_speed(
            conditions=simulator_conditions,
            current_speed_kmh=curr_speed,
            nearby_vehicles=nearby,
            next_maneuver=next_maneuver
        )
        
        # Check if current vehicle is on a living corridor
        living_corridor_active = False
        if curr_telemetry:
            # Simplistic check if we are near any corridor point
            corridors = self.living_map.get_road_corridors()
            for pt in corridors:
                if self._haversine(curr_telemetry.position, pt) < 20: # within 20 meters
                    living_corridor_active = True
                    break

        camera_state = "VEHICLE_CONTEXT" if len(self.context_vehicles) > 0 else "CLOSE_NAVIGATION"

        return NavigationState(
            current_vehicle=self.current_vehicle_id,
            current_position=p1 if curr_telemetry else None,
            heading=heading_deg if curr_telemetry else None,
            speed=speed_kmh if curr_telemetry else None,
            nearby_vehicles=nearby,
            active_route=self.active_route,
            route_source=self.active_route.source if self.active_route else None,
            destination=self.active_destination,
            distance_to_destination_m=dist_to_dest,
            next_maneuver=next_maneuver,
            maneuver_distance_m=maneuver_distance_m,
            maneuver_direction=maneuver_direction,
            camera_state=camera_state,
            governor=safety_decision.alert_severity,
            visibility="SIMULATED" if simulator_conditions.visibility == "FOG" else "NO LIVE LDR DATA",
            radar="NO LIVE DATA",
            living_corridor_active=living_corridor_active,
            safety_decision=safety_decision,
            data_sources={
                "gps": projection_mode if self.virtual_mode else "REAL PHONE GPS" if curr_telemetry else "UNKNOWN",
                "route": self.active_route.source if self.active_route else "NONE"
            },
            projection_mode=projection_mode,
            road_type=road_type,
            gradient_percent=gradient_percent
        )

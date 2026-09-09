from typing import List, Optional, Tuple
from datetime import datetime
import math
from core.models import SimulatorConditions, SafetyAlert, SafetyConstraint, SafetyDecision, Position, NearbyVehicle

# Configurable simulation parameters
GOVERNOR_REACTION_TIME_S = 1.5
GOVERNOR_ASSUMED_DECELERATION_MPS2 = 3.0
GOVERNOR_SAFETY_MARGIN_M = 5.0
BASE_ROAD_LIMIT_KMH = 30.0

class StoppingDistanceModel:
    @staticmethod
    def calculate_stopping_distance(speed_kmh: float) -> float:
        speed_mps = speed_kmh / 3.6
        reaction_distance = speed_mps * GOVERNOR_REACTION_TIME_S
        braking_distance = (speed_mps ** 2) / (2 * GOVERNOR_ASSUMED_DECELERATION_MPS2) if speed_mps > 0 else 0
        return reaction_distance + braking_distance + GOVERNOR_SAFETY_MARGIN_M

class VehicleConflictEvaluator:
    @staticmethod
    def evaluate(current_speed_kmh: float, nearby_vehicles: List[NearbyVehicle]) -> Tuple[Optional[float], Optional[SafetyAlert]]:
        closest_conflict_dist = float('inf')
        critical_conflict = False
        
        for nv in nearby_vehicles:
            # We don't have exact route overlap checking yet, but if it's very close and approaching, it's a conflict
            if nv.distance_m < closest_conflict_dist and nv.distance_m < 50:
                closest_conflict_dist = nv.distance_m
                
        if closest_conflict_dist == float('inf'):
            return None, None
            
        sd = StoppingDistanceModel.calculate_stopping_distance(current_speed_kmh)
        
        if closest_conflict_dist <= sd:
            alert = SafetyAlert(
                alert_type="VEHICLE",
                severity="CRITICAL",
                distance_m=closest_conflict_dist,
                message="Critical vehicle conflict",
                source="SIMULATOR",
                timestamp=datetime.utcnow(),
                active=True
            )
            return 0.0, alert
        elif closest_conflict_dist < 50:
            alert = SafetyAlert(
                alert_type="VEHICLE",
                severity="WARNING",
                distance_m=closest_conflict_dist,
                message="Vehicle approaching",
                source="SIMULATOR",
                timestamp=datetime.utcnow(),
                active=True
            )
            return 12.0, alert
            
        return None, None

class TurnEvaluator:
    @staticmethod
    def evaluate(maneuver: Optional[str]) -> Tuple[Optional[float], Optional[SafetyAlert]]:
        if not maneuver:
            return None, None
            
        if maneuver == "SHARP RIGHT" or maneuver == "SHARP LEFT":
            alert = SafetyAlert(
                alert_type="SHARP TURN",
                severity="WARNING",
                distance_m=None,
                message="Approaching sharp curve",
                source="SIMULATOR",
                timestamp=datetime.utcnow(),
                active=True
            )
            return 15.0, alert
        elif maneuver in ["RIGHT", "LEFT", "SLIGHT RIGHT", "SLIGHT LEFT"]:
            return 25.0, None # Normal turn constraint, no special alert
            
        return None, None

class DualConstraintGovernor:
    @staticmethod
    def calculate_safe_speed(conditions: SimulatorConditions, current_speed_kmh: float, nearby_vehicles: List[NearbyVehicle], next_maneuver: Optional[str]) -> SafetyDecision:
        constraints: List[SafetyConstraint] = []
        alerts: List[SafetyAlert] = []
        
        # 1. Base Limit
        constraints.append(SafetyConstraint(type="BASE_ROAD", limit_kmh=BASE_ROAD_LIMIT_KMH, reason="Base road limit"))
        
        # 2. Road Condition
        if conditions.road == "WET":
            constraints.append(SafetyConstraint(type="WET_ROAD", limit_kmh=15.0, reason="Reduced traction"))
            
        # 3. Visibility
        if conditions.visibility == "FOG":
            constraints.append(SafetyConstraint(type="FOG", limit_kmh=10.0, reason="Reduced visibility"))
            alerts.append(SafetyAlert(
                alert_type="FOG",
                severity="WARNING",
                distance_m=None,
                message="Simulated Fog",
                source="SIMULATOR",
                timestamp=datetime.utcnow(),
                active=True
            ))
            
        # 4. Turn Constraint
        turn_limit, turn_alert = TurnEvaluator.evaluate(next_maneuver)
        if turn_limit is not None:
            constraints.append(SafetyConstraint(type="TURN", limit_kmh=turn_limit, reason="Curve geometry"))
        if turn_alert:
            alerts.append(turn_alert)
            
        # 5. Obstacle / Pedestrian
        if conditions.obstacle == "PEDESTRIAN" or conditions.obstacle == "OBSTACLE":
            # Hardcoded distance for demo purposes since we don't have live radar
            hazard_dist = 20.0 
            sd = StoppingDistanceModel.calculate_stopping_distance(current_speed_kmh)
            
            if hazard_dist <= sd:
                constraints.append(SafetyConstraint(type=conditions.obstacle, limit_kmh=0.0, reason="Stopping distance exceeds clearance"))
                alerts.append(SafetyAlert(
                    alert_type="STOP" if conditions.obstacle == "OBSTACLE" else "PEDESTRIAN",
                    severity="CRITICAL",
                    distance_m=hazard_dist,
                    message="Critical hazard detected",
                    source="SIMULATOR",
                    timestamp=datetime.utcnow(),
                    active=True
                ))
            else:
                constraints.append(SafetyConstraint(type=conditions.obstacle, limit_kmh=10.0, reason="Hazard ahead"))
                alerts.append(SafetyAlert(
                    alert_type="PEDESTRIAN" if conditions.obstacle == "PEDESTRIAN" else "OBSTACLE",
                    severity="WARNING",
                    distance_m=hazard_dist,
                    message="Hazard ahead",
                    source="SIMULATOR",
                    timestamp=datetime.utcnow(),
                    active=True
                ))
                
        # 6. Vehicle Conflict
        veh_limit, veh_alert = VehicleConflictEvaluator.evaluate(current_speed_kmh, nearby_vehicles)
        if veh_limit is not None:
            constraints.append(SafetyConstraint(type="VEHICLE_CONFLICT", limit_kmh=veh_limit, reason="Closing vehicle"))
        if veh_alert:
            alerts.append(veh_alert)
            
        # Determine MOST RESTRICTIVE speed
        final_speed = min(c.limit_kmh for c in constraints)
        
        # Determine highest priority alert
        priority_map = {
            "STOP": 1,
            "PEDESTRIAN": 2,
            "VEHICLE": 3,
            "ROAD BLOCKED": 4,
            "FOG": 5,
            "SHARP TURN": 6,
            "NORMAL TURN": 7
        }
        
        best_alert = None
        best_priority = 99
        for a in alerts:
            p = priority_map.get(a.alert_type, 99)
            if p < best_priority:
                best_priority = p
                best_alert = a
                
        if not best_alert:
            best_alert = SafetyAlert(
                alert_type="CLEAR",
                severity="CLEAR",
                distance_m=None,
                message="No active hazards",
                source="SYSTEM",
                timestamp=datetime.utcnow(),
                active=False
            )
            
        # Find the dominant constraint reason
        reason = "Conditions clear"
        for c in constraints:
            if c.limit_kmh == final_speed and c.type != "BASE_ROAD":
                reason = c.reason
                break
                
        return SafetyDecision(
            permitted_speed_kmh=final_speed,
            active_alert=best_alert,
            alert_severity=best_alert.severity,
            reason=reason,
            constraints=[c.type for c in constraints]
        )

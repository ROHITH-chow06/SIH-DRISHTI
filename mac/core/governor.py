from datetime import datetime
from core.models import SimulatorConditions, GovernorDecision

def calculate_safe_speed(conditions: SimulatorConditions) -> GovernorDecision:
    """
    Calculates the safe operating speed using dual-constraint logic.
    """
    vis_limit = 30.0 if conditions.visibility == "CLEAR" else 10.0
    road_limit = 30.0 if conditions.road == "DRY" else 15.0
    
    if conditions.obstacle != "NONE":
        return GovernorDecision(
            state="STOP",
            recommended_speed_kmh=0.0,
            visibility_limit_kmh=vis_limit,
            road_condition_limit_kmh=road_limit,
            final_speed_limit_kmh=0.0,
            reason=f"Obstacle detected — STOP",
            timestamp=datetime.utcnow()
        )
        
    final_limit = min(vis_limit, road_limit)
    
    if final_limit == 30.0:
        state = "CLEAR"
        reason = "Conditions clear"
    elif final_limit == 15.0:
        state = "CAUTION"
        reason = "Reduced speed due to road conditions"
    else:
        state = "SLOW"
        reason = "Reduced speed due to visibility"
        
    return GovernorDecision(
        state=state,
        recommended_speed_kmh=final_limit,
        visibility_limit_kmh=vis_limit,
        road_condition_limit_kmh=road_limit,
        final_speed_limit_kmh=final_limit,
        reason=reason,
        timestamp=datetime.utcnow()
    )

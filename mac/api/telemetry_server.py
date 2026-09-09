import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, List, Optional
import uvicorn

from core.models import VehicleTelemetry, Position, RoadCorridorPoint, CandidateRoadSegment, SimulatorConditions, GovernorDecision, Alert, NavigationState, SafetyDecision
from datetime import datetime
from core.governor import calculate_safe_speed
from sources.phone_gps import PhoneGPSData, process_phone_gps
from core.models import SARMetadata
from core.config import SERVER_HOST, SERVER_PORT, GPS_DISPLAY_MODE, SAR_ANCHOR_LAT, SAR_ANCHOR_LON
from mapping.living_map import LivingMap
from mapping.sar_layer import SARLayer

# Configure basic logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="DRISHTI Telemetry Server")

# Allow CORS for the HTML prototype sender
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory unified state
latest_telemetry_store: Dict[str, VehicleTelemetry] = {}
simulator_conditions = SimulatorConditions()
sar_layer = SARLayer()
vehicle_anchors: Dict[str, Position] = {}
alert_log: List[Alert] = []

def add_alert(alert_type: str, message: str, vehicle_id: Optional[str] = None):
    alert = Alert(timestamp=datetime.utcnow(), type=alert_type, message=message, vehicle_id=vehicle_id)
    alert_log.insert(0, alert)
    if len(alert_log) > 50:
        alert_log.pop()

living_map = LivingMap(on_alert=add_alert)

from core.navigation import NavigationEngine, DESTINATIONS
nav_engine = NavigationEngine(living_map)

@app.post("/api/telemetry", response_model=VehicleTelemetry)
async def receive_phone_telemetry(data: PhoneGPSData):
    """
    Endpoint to receive GPS data from the phone prototype.
    """
    try:
        import math
        telemetry = process_phone_gps(data)
        
        if GPS_DISPLAY_MODE == "demo_anchored":
            telemetry.metadata.original_position = Position(
                latitude=telemetry.position.latitude,
                longitude=telemetry.position.longitude,
                altitude=telemetry.position.altitude
            )
            vid = telemetry.vehicle_id
            if vid not in vehicle_anchors:
                vehicle_anchors[vid] = telemetry.metadata.original_position
            
            anchor = vehicle_anchors[vid]
            delta_north_m = (telemetry.position.latitude - anchor.latitude) * 111320.0
            delta_east_m = (telemetry.position.longitude - anchor.longitude) * 111320.0 * math.cos(math.radians(anchor.latitude))
            
            telemetry.position.latitude = SAR_ANCHOR_LAT + (delta_north_m / 111320.0)
            telemetry.position.longitude = SAR_ANCHOR_LON + (delta_east_m / (111320.0 * math.cos(math.radians(SAR_ANCHOR_LAT))))
        
        latest_telemetry_store[telemetry.vehicle_id] = telemetry
        living_map.update_vehicle(telemetry)
        
        logger.info(f"[GPS] {telemetry.vehicle_id} position received")
        if data.accuracy_m is not None:
            logger.info(f"[GPS] accuracy: {data.accuracy_m:.2f} m")
        logger.info(f"[TELEMETRY] updated {telemetry.vehicle_id}")
        
        return telemetry
    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=422, detail=str(e))

@app.get("/api/vehicles", response_model=List[VehicleTelemetry])
async def get_all_vehicles():
    """
    Returns the latest telemetry for all known vehicles.
    """
    return list(latest_telemetry_store.values())

@app.get("/api/vehicles/{vehicle_id}", response_model=VehicleTelemetry)
async def get_vehicle(vehicle_id: str):
    """
    Returns the latest telemetry for a specific vehicle.
    """
    if vehicle_id not in latest_telemetry_store:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return latest_telemetry_store[vehicle_id]

@app.get("/api/map/vehicles", response_model=Dict[str, Optional[Position]])
async def get_map_vehicles():
    """
    Returns current position of every tracked vehicle on the map.
    """
    return living_map.get_current_positions()

@app.get("/api/map/trace/{vehicle_id}", response_model=List[Position])
async def get_map_vehicle_trace(vehicle_id: str):
    """
    Returns the historical GPS trace for a specific vehicle.
    """
    if vehicle_id not in living_map.get_tracked_vehicles():
        raise HTTPException(status_code=404, detail="Vehicle trace not found")
    return living_map.get_vehicle_trace(vehicle_id)

@app.get("/api/map/routes", response_model=List[CandidateRoadSegment])
async def get_routes():
    if nav_engine.virtual_mode:
        return [
            CandidateRoadSegment(
                route_id=r.route_id,
                path_coordinates=r.path_coordinates,
                source="DEMO VIRTUAL MINE",
                confidence=100.0,
                status="ACTIVE"
            ) for r in nav_engine.virtual_env.routes.values()
        ]
    return list(living_map.get_candidate_routes())

@app.get("/api/map/routes/{route_id}", response_model=CandidateRoadSegment)
async def get_candidate_route(route_id: str):
    """
    Returns a specific candidate route by ID.
    """
    for r in living_map.get_candidate_routes():
        if r.route_id == route_id:
            return r
    raise HTTPException(status_code=404, detail="Route not found")

@app.get("/api/map/road_corridors", response_model=List[RoadCorridorPoint])
async def get_road_corridors():
    """
    Returns the accumulated road trace / corridor network derived from vehicle GPS traces.
    """
    return living_map.get_road_corridors()

@app.get("/api/navigation/state", response_model=NavigationState)
async def get_navigation_state():
    """
    Returns the complete navigation context for the DRISHTI terminal.
    """
    return nav_engine.get_state(latest_telemetry_store, simulator_conditions)

@app.get("/api/navigation/safety", response_model=SafetyDecision)
async def get_safety_state():
    """
    Returns just the safety decision for the driver UI.
    """
    state = nav_engine.get_state(latest_telemetry_store, simulator_conditions)
    return state.safety_decision

@app.get("/api/map/sar/metadata", response_model=SARMetadata)
async def get_sar_metadata():
    """
    Returns Sentinel-1 SAR metadata.
    """
    return sar_layer.get_metadata()

@app.get("/api/config/gps_mode")
async def get_gps_mode():
    """Returns the current GPS display mode."""
    return {"mode": GPS_DISPLAY_MODE}

@app.get("/")
async def serve_dashboard():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'dashboard.html')
    return FileResponse(file_path)

@app.get("/strip")
async def serve_strip():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'strip.html')
    return FileResponse(file_path)

@app.get("/api/alerts", response_model=List[Alert])
async def get_alerts():
    return alert_log

@app.get("/map")
async def serve_living_map():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'living_map.html')
    return FileResponse(file_path)

@app.get("/simulator")
async def serve_simulator():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'simulator.html')
    return FileResponse(file_path)

@app.get("/api/simulator/state", response_model=SimulatorConditions)
async def get_simulator_state():
    return simulator_conditions

@app.post("/api/simulator/conditions", response_model=SimulatorConditions)
async def update_simulator_conditions(conditions: SimulatorConditions):
    global simulator_conditions
    
    # Check for changes to generate alerts
    old_state = calculate_safe_speed(simulator_conditions).state
    
    if simulator_conditions.visibility != conditions.visibility:
        if conditions.visibility == "FOG":
            add_alert("WARNING", "Fog enabled")
        else:
            add_alert("INFO", "Fog cleared")
            
    if simulator_conditions.road != conditions.road:
        if conditions.road == "WET":
            add_alert("WARNING", "Wet road enabled")
        else:
            add_alert("INFO", "Dry road restored")
            
    if simulator_conditions.obstacle != conditions.obstacle:
        if conditions.obstacle == "PEDESTRIAN":
            add_alert("CRITICAL", "Pedestrian detected")
        elif conditions.obstacle == "OBSTACLE":
            add_alert("CRITICAL", "Obstacle detected")
        elif conditions.obstacle == "NONE":
            add_alert("INFO", "Obstacle cleared")
            
    simulator_conditions = conditions
    
    new_state = calculate_safe_speed(simulator_conditions).state
    if old_state != new_state:
        if new_state == "STOP":
            add_alert("CRITICAL", "Governor changed to STOP")
        elif new_state == "SLOW":
            add_alert("WARNING", "Governor changed to SLOW")
        elif new_state in ["CLEAR", "CAUTION"] and old_state in ["SLOW", "STOP"]:
            add_alert("INFO", f"Governor returned to {new_state}")
            
    return simulator_conditions

@app.get("/api/governor/state", response_model=GovernorDecision)
async def get_governor_state():
    return calculate_safe_speed(simulator_conditions)

@app.get("/gps")
async def serve_gps_sender():
    """
    Serves the HTML5 GPS sender page.
    """
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sources', 'gps_sender.html')
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="GPS sender page not found")
    return FileResponse(file_path)

# --- NAVIGATION ENDPOINTS ---

from pydantic import BaseModel
class SetVehicleRequest(BaseModel):
    vehicle_id: str

class SetDestinationRequest(BaseModel):
    destination_name: str

@app.post("/api/navigation/vehicle")
async def nav_set_vehicle(req: SetVehicleRequest):
    nav_engine.set_current_vehicle(req.vehicle_id)
    return {"status": "ok", "current_vehicle": nav_engine.current_vehicle_id}

@app.post("/api/navigation/destination")
async def nav_set_destination(req: SetDestinationRequest):
    nav_engine.set_destination(req.destination_name)
    return {"status": "ok", "active_destination": req.destination_name}

@app.get("/api/navigation/destinations")
async def nav_get_destinations():
    return DESTINATIONS

# --- Virtual Mine Endpoints ---

class VirtualModeRequest(BaseModel):
    enabled: bool

@app.post("/api/navigation/virtual-mode")
async def nav_set_virtual_mode(req: VirtualModeRequest):
    nav_engine.virtual_mode = req.enabled
    return {"status": "ok", "virtual_mode": nav_engine.virtual_mode}

@app.post("/api/navigation/virtual-reset")
async def nav_virtual_reset():
    nav_engine.reset_virtual_state()
    return {"status": "ok"}

@app.get("/api/navigation/virtual-routes")
async def nav_get_virtual_routes():
    routes = nav_engine.virtual_env.routes
    return [{"route_id": r.route_id, "name": r.name, "road_type": r.road_type} for r in routes.values()]

class VirtualDestinationRequest(BaseModel):
    destination_name: str

@app.post("/api/navigation/virtual-destination")
async def nav_set_virtual_destination(req: VirtualDestinationRequest):
    nav_engine.set_destination(req.destination_name)
    return {"status": "ok", "virtual_destination": req.destination_name}

@app.get("/api/navigation/virtual-state")
async def nav_get_virtual_state():
    states = list(nav_engine.projector.virtual_states.values())
    return [s.dict() for s in states]

# --- Base Navigation ---
@app.get("/api/navigation/state")
async def nav_get_state():
    from core.models import NavigationState
    state = nav_engine.get_state(latest_telemetry_store, simulator_conditions)
    return state

@app.get("/navigation")
async def serve_navigation():
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'navigation.html')
    return FileResponse(file_path)

if __name__ == "__main__":
    cert_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'certs', 'cert.pem')
    key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'certs', 'key.pem')
    
    if os.path.exists(cert_path) and os.path.exists(key_path):
        logger.info(f"Starting DRISHTI Telemetry Server (HTTPS) on {SERVER_HOST}:{SERVER_PORT}")
        uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT, ssl_keyfile=key_path, ssl_certfile=cert_path)
    else:
        logger.info(f"Starting DRISHTI Telemetry Server (HTTP) on {SERVER_HOST}:{SERVER_PORT}")
        uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)

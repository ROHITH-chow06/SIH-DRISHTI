# DRISHTI — Intelligent V2V Braking & Vehicle Safety System

> A multidisciplinary prototype combining Vehicle-to-Vehicle (V2V) communication, radar sensing, visibility sensing, embedded control, mechatronics, telemetry, mapping, simulation, and safety-oriented decision logic.

## Overview

DRISHTI explores how multiple vehicles can share safety information and respond to hazards cooperatively. The prototype combines an ESP32-based physical vehicle system with a computer-side telemetry and navigation stack.

The vehicle node acquires obstacle information from an HLK-LD2450 mmWave radar and visibility information from an LDR-based sensor. It processes these signals locally, generates warnings, demonstrates prototype-scale motor stopping when the configured radar threshold is crossed, and broadcasts vehicle state using ESP-NOW.

A second ESP32 receives the V2V message and demonstrates how a nearby vehicle can react to another vehicle's warning state. The wider software stack extends the prototype with Python telemetry, MQTT, GPS vehicle tracking, a Living Map, road-corridor accumulation, candidate-route modelling, and a supervisory navigation/Governor layer.

## Why DRISHTI Fits Intelligent V2V Braking

The project brings together the major technical areas expected in a V2V/ADAS research environment:

**Automotive Systems → Embedded Systems → Sensors → Signal Processing → V2V Communication → Control → Mechatronics → Simulation → Backend Software → Telemetry → Mapping → Safety Logic → Testing → Documentation**

## Skills Demonstrated

### 1. Automotive, ADAS & V2V Concepts

- Vehicle-to-Vehicle communication concepts
- Cooperative safety and warning propagation
- ADAS-style obstacle detection
- Proximity-based safety decisions
- Vehicle state sharing
- Multi-vehicle safety architecture
- Understanding of the relationship between sensing, communication and control

### 2. Embedded Systems & ESP32

- ESP32 firmware development
- Arduino/C++ programming
- GPIO configuration
- ADC configuration and calibration
- UART / Serial2 communication
- Embedded timing using `millis()`
- State-based control logic
- Hardware/software integration
- Serial diagnostics and debugging

### 3. Radar & Sensor Integration

- HLK-LD2450 mmWave radar integration
- UART communication at 256000 baud
- Binary radar-frame parsing
- Frame header/footer validation
- Signed coordinate decoding
- Distance calculation from X/Y coordinates
- Radar freshness/staleness handling
- LDR-based visibility sensing
- Sensor calibration and sanity checks

### 4. Signal Processing & Calibration

- ADC sampling and averaging
- Clear-reference calibration
- Percentage normalization
- Threshold classification
- Hysteresis
- Sensor-noise and glitch handling
- Conversion of raw sensor readings into system states

### 5. V2V / Wireless Communication

- ESP-NOW
- Broadcast communication
- Sender/receiver architecture
- Shared binary message structures
- Packet-length validation
- Wireless state propagation
- Communication freshness/timeouts
- Multi-vehicle warning exchange

### 6. Control Systems & Prototype Braking

- Event-driven control logic
- Obstacle-triggered stopping
- Motor direction control
- L293D motor-driver integration
- Relay integration
- Braking-state management
- Threshold tuning
- Stopping-distance validation
- Relationship between trigger distance and physical stopping behaviour

`BRAKE_CM` is a scaled-prototype demonstration parameter and is not a real-vehicle stopping specification.

### 7. Mechatronics & Hardware Integration

- ESP32 + sensors + motor-driver integration
- DC motor control
- Relay and motor-supply integration
- Power-path analysis
- Electrical-noise troubleshooting
- Wiring verification
- Capacitor-based transient/noise mitigation
- Chassis-level prototype integration
- Controlled hardware bring-up

### 8. Debugging & Engineering Problem Solving

The development involved real hardware/software troubleshooting rather than assuming that the first implementation would work. Issues included radar TX/RX wiring, incorrect UART baud rate, radar/power instability, LDR calibration, ESP32 ADC/Wi-Fi interaction, motor direction, L293D enable/control wiring, motor electrical noise, relay paths, ESP-NOW sender/receiver compatibility, receiver freshness, GPS/browser limitations, and telemetry/model consistency.

The engineering workflow was:

**Observe → Reproduce → Isolate → Diagnose → Modify → Test → Validate → Document**

### 9. Python & Backend Development

- Python programming
- FastAPI
- REST API design
- Pydantic data models
- Asynchronous endpoints
- Telemetry processing
- Logging
- Modular backend architecture

### 10. MQTT & IoT

- MQTT publish/subscribe architecture
- Serial-to-network telemetry bridging
- Device-to-computer communication
- Event/state messaging
- Separation of embedded and application layers

### 11. GPS, Mapping & Geospatial Data

- GPS telemetry
- Vehicle position tracking
- Historical GPS traces
- Multi-vehicle map visualisation
- Road-corridor accumulation
- Candidate-route modelling
- Route confidence concepts

### 12. Simulation & Modelling

- Vehicle/safety scenario modelling
- Visibility-condition modelling
- Obstacle-state modelling
- Governor/safety-state modelling
- Safe-speed decision logic
- Simulation-driven validation

### 13. Safety Logic & Decision Systems

- Deterministic safety rules
- Multi-sensor warning conditions
- Radar-based proximity decisions
- Visibility-aware states
- Sensor freshness checks
- Fail-aware state handling
- Safety alerts
- Supervisory decision architecture

### 14. Testing & Validation

- Controlled experiments
- Sensor-only testing
- Communication testing
- Motor-driver testing
- Integrated-system testing
- Visibility/fog demonstration
- Stopping-distance measurement
- Repeated-run validation
- Calibration checks
- Fault isolation
- Test-result documentation

### 15. Technical Documentation & Communication

- Engineering reports
- System architecture documentation
- Hardware build documentation
- Software documentation
- Debugging records
- Test procedures
- Results tables
- Technical presentations
- Design-decision communication
- Knowledge transfer

## Physical Prototype

The physical prototype demonstrates the mechatronics side of DRISHTI using an ESP32 vehicle controller, mmWave radar, LDR visibility sensor, motor driver, relay, LEDs, alert output, DC motors and a second ESP32 receiver.

The repository's `assets/` directory is intended for prototype photographs and system visuals.

## System Architecture

```text
                   ┌───────────────────────┐
                   │   Vehicle 1 / Node    │
                   │                       │
                   │ LD2450 Radar          │
                   │ LDR Visibility Sensor │
                   │ ESP32                 │
                   │ Warning + Motor Logic │
                   └───────────┬───────────┘
                               │
                               │ ESP-NOW
                               ▼
                   ┌───────────────────────┐
                   │   Vehicle 2 / Node    │
                   │                       │
                   │ ESP32 Receiver        │
                   │ Message Validation    │
                   │ Freshness Check       │
                   │ Warning Output        │
                   └───────────┬───────────┘
                               │
                               │ Serial
                               ▼
                   ┌───────────────────────┐
                   │   Python / MQTT       │
                   │ Telemetry Backend     │
                   └───────────┬───────────┘
                               │
              ┌────────────────┼─────────────────┐
              ▼                ▼                 ▼
       ┌────────────┐   ┌─────────────┐   ┌──────────────┐
       │ Living Map │   │ Navigation  │   │ Simulator /  │
       │ & GPS      │   │ / Governor  │   │ Safety Logic │
       └────────────┘   └─────────────┘   └──────────────┘
```

## Technology Stack

| Area | Technologies / Concepts |
|---|---|
| Microcontroller | ESP32 |
| Firmware | Arduino C++ |
| Radar | HLK-LD2450 mmWave |
| Visibility | LDR + LED sensor |
| Motor Driver | L293D |
| Wireless | ESP-NOW |
| Serial | UART |
| Backend | Python + FastAPI |
| Messaging | MQTT |
| Positioning | Phone GPS / GPS telemetry |
| Mapping | Living Map / geospatial traces |
| Simulation | Python-based vehicle/safety modelling |
| Web | HTML / JavaScript components |
| Version Control | Git + GitHub |

## Development Methodology

The system was developed incrementally so that individual subsystems could be validated before full integration:

1. ESP32 bring-up and programming verification
2. Radar-only sensing
3. LDR sensing and calibration
4. Local warning outputs
5. ESP-NOW vehicle-to-vehicle communication
6. Motor and relay integration
7. Combined radar/braking prototype
8. Full sensing + V2V + braking integration
9. Controlled visibility demonstration
10. Serial/MQTT computer integration
11. Multi-vehicle GPS Living Map
12. Road-corridor accumulation
13. Candidate-route modelling
14. Navigation/Governor architecture

## Mapping to the Intelligent V2V Braking Internship

| Internship Requirement | DRISHTI Skill Match |
|---|---|
| Automotive systems | ADAS/V2V concepts, vehicle sensing, braking prototype |
| Simulation | Vehicle/safety simulation and Governor modelling |
| Mechatronics | ESP32, sensors, motors, L293D, relay, physical prototype |
| Programming / coding | Arduino C++, Python, FastAPI, JavaScript, MQTT |
| Creating drawings, models or designs | System architecture, physical vehicle, mapping and safety models |
| Mathematical problem solving | Coordinate processing, distance calculation, thresholds and stopping-distance analysis |
| Controlled experiments | Sensor, communication, visibility and braking tests |
| Laboratory equipment | ESP32, radar, LDR, motors and electronics |
| Data analysis | Sensor readings, telemetry, GPS traces and test results |
| Research literature / documents | Development-record analysis and iterative implementation |
| Teamwork | Embedded, backend, mapping and navigation integration |
| Report writing | Build, debugging, architecture and validation documentation |
| Supervisor discussions | Design review and technical presentation readiness |
| Time management | Incremental development and subsystem validation |
| Creative/self-motivated work | Iterative troubleshooting and system extension |

## Core Engineering Challenges

**Radar:** UART configuration, binary frame synchronization, signed coordinate decoding, distance calculation and stale-data handling.

**Visibility:** clear-light calibration, normalization, sanity checks and hysteresis for stable visibility states.

**Motor control:** enable/control wiring, motor direction, relay paths, power interaction and electrical noise.

**V2V:** compatible sender/receiver message structures, packet validation and freshness handling.

**Computer integration:** serial communication, Python, MQTT, GPS, mapping and browser-based visualisation.

## Safety & Prototype Scope

DRISHTI is a research/prototype platform. The physical vehicle is a scaled demonstration system and does not represent the dynamics, braking performance, environmental qualification, cybersecurity, or certification requirements of a full-size mining or road vehicle.

Production deployment would require formal hazard analysis, validated industrial sensors, safety-rated vehicle interfaces, environmental testing, secure V2X communication, and regulatory approval.

## Repository Structure

```text
firmware/
├── vehicle_node/
│   └── vehicle_node.ino
└── v2v_receiver/
    └── v2v_receiver.ino

assets/
├── 01_vehicle_prototype.jpeg
├── 02_v2v_receiver.jpeg
└── 03_integrated_vehicle.jpeg
```

## Core Learning Outcome

The strongest capability demonstrated by DRISHTI is **systems engineering**: integrating sensors, embedded hardware, wireless V2V communication, control logic, mechatronics, software services, mapping, simulation and safety decisions into one coherent prototype.

This combination makes DRISHTI relevant to **V2V/V2X, ADAS, automotive electronics, autonomous systems, robotics, mechatronics, embedded systems, IoT, simulation and safety engineering**.

## Keywords

`V2V` `V2X` `ADAS` `Embedded Systems` `ESP32` `Arduino C++` `HLK-LD2450` `mmWave Radar` `Sensor Processing` `LDR` `UART` `ADC` `ESP-NOW` `Motor Control` `L293D` `Mechatronics` `Prototype Braking` `Python` `FastAPI` `MQTT` `GPS` `Geospatial Mapping` `Simulation` `Safety Systems` `Control Systems` `IoT` `Git` `GitHub` `Systems Engineering`

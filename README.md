# DRISHTI Firmware

Verified firmware set for the ESP32 prototype: LD2450 radar sensing, LDR-based visibility classification, prototype autonomous stopping logic, and ESP-NOW vehicle-to-vehicle warning.

## Canonical sketches

- `firmware/vehicle_node/vehicle_node.ino` — sensor + drive node
- `firmware/v2v_receiver/v2v_receiver.ino` — V2V receiver

Earlier sketches were diagnostic or partial. The canonical files contain the integrated logic and fixes selected from the development record.

## Vehicle node

- LD2450 UART2 on GPIO16/17 at 256000 baud
- LDR on GPIO34
- Red/green indicators on GPIO18/19
- Alert output on GPIO23
- L293D motor control on GPIO4/5
- ESP-NOW broadcast
- LDR calibration before Wi-Fi/ESP-NOW startup
- LDR glitch guard
- 30-byte radar frame validation
- 500 ms radar freshness timeout
- Single-shot prototype braking using `BRAKE_CM`

## V2V receiver

- Receives the identical `Msg` structure over ESP-NOW
- 2-second freshness window
- LED and Serial warning output

## Prototype note

`BRAKE_CM` is a scaled-vehicle demonstration parameter, not a real-vehicle stopping specification. The prototype must be tested and calibrated before demonstration.

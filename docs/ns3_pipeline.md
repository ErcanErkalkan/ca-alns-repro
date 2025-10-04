# ns-3 Packet-Level Validation Pipeline

This document outlines how to produce PDR/Delay/Hop metrics with ns-3 to validate connectivity at the packet level.

## Steps

1. **Export traces** (from CA-ALNS runs):
   ```bash
   make ns3-export SCALE=Medium ALGO=ca-alns
   ```

2. **Run ns-3**:
   - Implement `scratch/fanet_validate.cc` (or Python bindings) to read `ns3_traces/Medium/`
   - Use `WaypointMobilityModel` for UAV mobility (from traces)
   - Configure WiFi (e.g., 802.11n, 20 MHz, Tx power 20 dBm)
   - Use OLSR or AODV routing
   - Write logs to `ns3_logs/Medium/`

3. **Aggregate**:
   ```bash
   make ns3-aggregate SCALE=Medium
   ```

4. **Plot**:
   ```bash
   make ns3-plots SCALE=Medium
   ```

## PHY/MAC (example)

- Tx power: 20 dBm, Antenna gain: 2 dBi
- Bandwidth: 20 MHz
- SINR threshold: 6 dB
- Path loss: Friis + Nakagami (LoS/NLoS probabilities by altitude/distance)

Make sure these match the parameters in the paper tables.

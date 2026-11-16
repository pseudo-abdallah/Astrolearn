# Mount control

Owns device connection, status, pointing, tracking, stop, and configured movement limits.

Implement a simulator before connecting physical hardware. Serialize conflicting commands and do not replay motion after reconnect or restart. Require explicit backend control actions and validate coordinates, units, and device state.

Choose the hardware protocol after identifying the actual mount and operating system.

Status: implementation pending.

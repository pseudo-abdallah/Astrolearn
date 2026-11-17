"""Extension boundary: no GPIO, camera, or motor behavior is assumed."""

from typing import Protocol


class HardwareStatus(Protocol):
    """A future confirmed adapter must report its availability truthfully."""

    def status(self) -> dict[str, str | bool]: ...


class DisconnectedHardware:
    """Default adapter never opens a device or pretends a command succeeded."""

    def status(self) -> dict[str, str | bool]:
        return {"connected": False, "mode": "disconnected"}

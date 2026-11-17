"""Bench-only mount simulation. No serial connection or real motor is implied."""

import time
from threading import Lock

from pydantic import BaseModel, ConfigDict, Field


class MoveRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    axis: str = Field(pattern='^(ra|dec)$')
    steps: int = Field(ge=-100000, le=100000, strict=True)


class SimulatedMount:
    def __init__(self):
        self.lock = Lock()
        self.positions = {'ra': 0, 'dec': 0}
        self.state = 'idle'
        self.motion = None
        self.pointing = {'ra_deg': 0., 'dec_deg': 0., 'altitude_deg': 0., 'azimuth_deg': 0.}
        self.target = None
        self.slew = None
        self.command_versions = {}

    def _update(self):
        if self.slew:
            start, goal, began = self.slew
            fraction = min(1, (time.monotonic() - began) / 3)
            for key in self.pointing:
                delta = goal[key] - start[key]
                if key in {'ra_deg', 'azimuth_deg'}:
                    delta = (delta + 180) % 360 - 180
                value = start[key] + fraction * delta
                self.pointing[key] = value % 360 if key in {'ra_deg', 'azimuth_deg'} else value
            if fraction >= 1:
                self.slew = None
                self.state = 'idle'
        if self.motion:
            axis, start, steps, began, duration = self.motion
            fraction = min(1, (time.monotonic() - began) / duration)
            self.positions[axis] = start + round(steps * fraction)
            if fraction >= 1:
                self.motion = None
                self.state = 'idle'

    def status(self):
        with self.lock:
            self._update()
            return {'mode': 'simulation', 'state': self.state, 'positions_steps': dict(self.positions),
                    'pointing': dict(self.pointing), 'target': self.target,
                    'physical_hardware': False, 'tracking': False}

    def move(self, command: MoveRequest):
        with self.lock:
            self._update()
            if self.state == 'stopped':
                raise ValueError('Reset the simulated stop before moving.')
            if self.motion:
                raise ValueError('Simulated mount is busy.')
            self.motion = (command.axis, self.positions[command.axis], command.steps, time.monotonic(), 3)
            self.slew = None
            self.state = 'moving'
        return self.status()

    def stop(self):
        with self.lock:
            self._update()
            self.motion = None
            self.slew = None
            self.state = 'stopped'
        return self.status()

    def goto(self, position, client_id, sequence):
        """Coordinate-only simulation; no real axis calibration is implied.

        A newer selection supersedes an older selection still being calculated.
        Manual step commands remain available through the original API.
        """
        with self.lock:
            self._update()
            if self.state == 'stopped':
                raise ValueError('Simulator stopped. Resume it before choosing another target.')
            if sequence <= self.command_versions.get(client_id, 0):
                raise ValueError('A newer target selection has already been applied.')
            self.command_versions[client_id] = sequence
            if len(self.command_versions) > 64:
                del self.command_versions[next(iter(self.command_versions))]
            goal = {key: float(position[key]) for key in self.pointing}
            self.target = {'id': position['target']['id'], 'name': position['target']['name'],
                           'utc': position['utc'], 'destination': goal}
            self.motion = None
            self.slew = (dict(self.pointing), goal, time.monotonic())
            self.state = 'moving'
        return self.status()

    def reset(self):
        with self.lock:
            if self.state != 'stopped':
                raise ValueError('Stop the simulation before reset.')
            self.state = 'idle'
        return self.status()

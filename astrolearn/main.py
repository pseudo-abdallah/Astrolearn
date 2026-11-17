"""Application factory: each instance owns its storage and hardware adapter."""

import os
import asyncio
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from astrolearn import __version__
from astrolearn.hardware import DisconnectedHardware, HardwareStatus
from astrolearn.models import LearningObject, Observation, ObservationCreate
from astrolearn.storage import ObservationStore
from astrolearn.prototype import Prototype
from astrolearn.learning import learning_router
from astrolearn.solar import solar_router
from astrolearn.automatic import automatic_router

# Seed content is illustrative, not a visibility forecast or pointing catalogue.
CATALOG = (
    LearningObject(id="moon", name="Moon", category="natural satellite",
                   description="Earth's natural satellite. Its visible phase changes over time."),
    LearningObject(id="jupiter", name="Jupiter", category="planet",
                   description="A gas giant and the largest planet in our Solar System."),
    LearningObject(id="saturn", name="Saturn", category="planet",
                   description="A gas giant surrounded by a prominent ring system."),
)


def create_app(db_path: Path | None = None, hardware: HardwareStatus | None = None, solver=None) -> FastAPI:
    store = ObservationStore(db_path if db_path is not None else Path(
        os.environ.get("ASTROLEARN_DB_PATH", "data/astrolearn.sqlite3")
    ))
    adapter = hardware if hardware is not None else DisconnectedHardware()
    prototype = Prototype(store.path, solver)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Importing this module has no filesystem or device side effects.
        store.initialize()
        prototype.start()
        yield
        prototype.close()

    app = FastAPI(title="AstroLearn API", version=__version__, lifespan=lifespan)

    @app.middleware('http')
    async def fresh_local_ui(request, call_next):
        response = await call_next(request)
        if request.url.path == '/' or request.url.path.startswith('/static/'):
            response.headers['Cache-Control'] = 'no-cache'
        return response
    app.include_router(prototype.router())
    app.include_router(learning_router(prototype))
    app.include_router(solar_router(prototype))
    app.include_router(automatic_router(prototype))

    @app.websocket('/api/v1/telemetry')
    async def telemetry(websocket: WebSocket):
        await websocket.accept()
        sequence = 0
        try:
            while True:
                sequence += 1
                await websocket.send_json({'schema': 1, 'event': 'status.snapshot', 'sequence': sequence,
                    'utc': datetime.now(timezone.utc).isoformat(), 'camera': 'not configured',
                    'mount': prototype.mount.status(), 'mode': 'local image-only prototype'})
                # Read disconnects as well as sending snapshots; otherwise an
                # idle subscriber can leave an orphan stream after closing.
                try:
                    message = await asyncio.wait_for(websocket.receive(), timeout=1)
                    if message['type'] == 'websocket.disconnect':
                        break
                except asyncio.TimeoutError:
                    pass
        except (WebSocketDisconnect, RuntimeError, asyncio.CancelledError):
            pass
    assets = Path(__file__).with_name('static')
    app.mount('/static', StaticFiles(directory=assets), name='static')

    @app.get("/")
    def root():
        return FileResponse(assets / 'index.html')

    @app.get('/api/v1/info')
    def info():
        return {"name": "AstroLearn", "version": __version__, "docs": "/docs"}

    @app.get("/api/v1/health")
    def health():
        return {"status": "ok", "version": __version__}

    @app.get("/api/v1/status")
    def status():
        return {"hardware": adapter.status(), "capabilities": {
            "educational_catalog": True, "observation_log": True,
            "camera_capture": False, "motor_control": False, "automatic_pointing": False,
        }}

    @app.get("/api/v1/objects", response_model=list[LearningObject])
    def objects():
        return CATALOG

    @app.get("/api/v1/objects/{object_id}", response_model=LearningObject)
    def get_object(object_id: str):
        for item in CATALOG:
            if item.id == object_id:
                return item
        raise HTTPException(404, "Educational object not found")

    @app.post("/api/v1/observations", response_model=Observation, status_code=201)
    def create_observation(item: ObservationCreate):
        # Logging a note does not claim that hardware observed this target.
        return store.create(item)

    @app.get("/api/v1/observations", response_model=list[Observation])
    def observations(limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)):
        return store.list(limit, offset)

    @app.get("/api/v1/observations/{observation_id}", response_model=Observation)
    def get_observation(observation_id: int):
        item = store.get(observation_id)
        if item is None:
            raise HTTPException(404, "Observation not found")
        return item

    return app


app = create_app()

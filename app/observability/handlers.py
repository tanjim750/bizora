from app.events import subscribe


def handle_observation(event):
    from .services import record_observation
    return record_observation(**event.payload)


def register():
    subscribe('integration.observation', handle_observation)

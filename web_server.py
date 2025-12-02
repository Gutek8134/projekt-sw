from multiprocessing import Queue
from multiprocessing.synchronize import Event


def web_server(message_queue: "Queue[str]", playlist_update_event: Event) -> None:
    pass

from multiprocessing import Queue
from multiprocessing.synchronize import Event
from multiprocessing.managers import DictProxy


def web_server(user_rfids: "DictProxy[str, str]", message_queue: "Queue[str]", playlist_update_event: Event) -> None:
    pass

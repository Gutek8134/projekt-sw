from multiprocessing import Queue
from multiprocessing.synchronize import Event
from multiprocessing.managers import DictProxy


def web_server(shared_playlists: "DictProxy[str, list[tuple[time, str, str]]]",user_rfids: "DictProxy[str, str]", message_queue: "Queue[str]", playlist_update_event: Event) -> None:
    while True:
        input_from_terminal=input()
        if input_from_terminal == "STOP":
            message_queue.put("STOP")
            break
        else:
            input_from_terminal_split = input_from_terminal.strip().split()
            command = input_from_terminal_split[0]
            arguments = input_from_terminal_split[1:]
            match command:
                case "add_song":
                    if len(arguments) < 4:
                        print("Usage: add_song <user> <HH:MM> <title> <path>")
                        continue
                    user, time_string, title, path = (arguments[0],arguments[1],arguments[2],arguments[3],)
                    try:
                        hour, minute = map(int, time_string.split(":"))
                        time_object = time(hour, minute)
                    except Exception:
                        print("Invalid time format. Use HH:MM")
                        continue
                    if user not in shared_playlists:
                        shared_playlists[user] = []

                    shared_playlists[user].append((time_object, title, path))
                    playlist_update_event.set()
                    print(f"Added song to {user}'s playlist.")

                case "remove_song":
                    if len(arguments) < 2:
                        print("Usage: remove_song <user> <title>")
                        continue

                    user, title = arguments[0], arguments[1]

                    if user not in shared_playlists:
                        print("User not found.")
                        continue

                    before = len(shared_playlists[user])
                    shared_playlists[user] = [entry for entry in shared_playlists[user] if entry[1] != title]

                    if len(shared_playlists[user]) != before:
                        playlist_update_event.set()
                        print(f"Removed '{title}' from {user}'s playlist.")
                    else:
                        print("Song not found.")

                case "list_playlist":
                    if len(arguments) < 1:
                        print("Usage: list_playlist <user>")
                        continue
                    user = arguments[0]
                    if user not in shared_playlists:
                        print("User not found.")
                        continue
                    print(f"Playlist for {user}:")
                    for t, title, path in shared_playlists[user]:
                        print(f"  {t}  |  {title}  |  {path}")

                case "add_rfid":
                    if len(arguments) < 2:
                        print("Usage: add_rfid <rfid> <user>")
                        continue

                    rfid, user = arguments[0], arguments[1]
                    user_rfids[rfid] = user
                    print(f"RFID {rfid} assigned to user {user}.")

                case "remove_rfid":
                    if len(arguments) < 1:
                        print("Usage: remove_rfid <rfid>")
                        continue
                    rfid = arguments[0]
                    if rfid in user_rfids:
                        del user_rfids[rfid]
                        print(f"RFID {rfid} removed.")
                    else:
                        print("RFID not found.")
                    
                case "list_rfid_users":
                    print("RFID → User mapping:")
                    for rfid, user in user_rfids.items():
                        print(f"{rfid} : {user}")

                case "save":
                    message_queue.put("save")
                    print("Save requested.")

                case "load":
                    message_queue.put("load")
                    print("Load requested.")
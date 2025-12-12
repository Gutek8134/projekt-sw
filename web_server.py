from multiprocessing import Queue
from threading import Event
from multiprocessing.managers import DictProxy, ValueProxy, ListProxy, SyncManager
from datetime import time
from flask import Flask, render_template, after_this_request, Response, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os.path

UPLOAD_FOLDER = './music'
ALLOWED_EXTENSIONS = {"mp3"}


def web_server(shared_playlists: "DictProxy[str, ListProxy[tuple[time, str, str]]]", user_rfids: "DictProxy[str, str]", message_queue: "Queue[str]", playlist_update_event: Event, last_read_rfid: ValueProxy, current_user: ValueProxy, manager: SyncManager) -> None:
    flask = Flask(__name__)
    flask.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    flask.secret_key = "secret key"

    @flask.route("/")
    def index():
        songs: dict[str, list[str]] = {}
        if not os.path.exists(UPLOAD_FOLDER):
            os.mkdir(UPLOAD_FOLDER)
        for album in os.listdir(UPLOAD_FOLDER):
            songs[album] = []
            for song in os.listdir(os.path.join(UPLOAD_FOLDER, album)):
                songs[album].append(song)

        if os.name == "posix":
            return render_template("index.html", users=shared_playlists.keys(), playlists=shared_playlists, rfid=last_read_rfid.get(), songs=songs.items() if songs else list(songs.items()), current_user=current_user.get())
        # windows
        return render_template("index.html", users=shared_playlists.keys(), playlists=shared_playlists, rfid=last_read_rfid.value, songs=songs.items() if songs else list(songs.items()), current_user=current_user.value)

    @flask.route("/rfid", methods=["GET"])
    def get_last_rfid():
        @after_this_request
        def add_header(response: Response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

        if os.name == "posix":
            return {"text": last_read_rfid.get()}
        return {"text": last_read_rfid.value}  # windows

    def allowed_file(filename: str):
        return '.' in filename and \
            filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    @flask.route('/upload', methods=['POST'])
    def upload_file():
        # check if the post request has the file part
        if 'file' not in request.files:
            flash('No file part')
            return "FAILED"
        file = request.files['file']

        assert file.filename is not None
        # If the user does not select a file, the browser submits an
        # empty file without a filename.
        if file.filename == '':
            flash('No selected file')
            return "FAILED"

        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename).lower()
            if not os.path.exists(flask.config['UPLOAD_FOLDER']):
                os.mkdir(flask.config['UPLOAD_FOLDER'])
            if not os.path.exists(os.path.join(flask.config['UPLOAD_FOLDER'], request.form["album"])):
                os.mkdir(os.path.join(
                    flask.config['UPLOAD_FOLDER'], request.form["album"]))
            save_path = os.path.join(
                flask.config['UPLOAD_FOLDER'], request.form["album"], filename)
            file.save(save_path)
        return "SUCCESS"

    @flask.route("/add_user", methods=["POST"])
    def add_user():
        username = request.form.get("username")
        # check if empty argument
        if not username:
            flash('Empty username')
            return "FAILED"
        # check if username exits
        if username in shared_playlists:
            flash('Username already exists')
            return "FAILED"

        shared_playlists[username] = manager.list()
        return "SUCCESS"

    @flask.route("/assign_rfid", methods=["POST"])
    def assign_rfid():
        username = request.form.get("username")
        rfid = request.form.get("rfid")
        if rfid == "None":
            flash('Scan RFID')
            return "FAILED"
        if not username or not rfid:
            flash('Empty username or rfid')
            return "FAILED"

        if username not in shared_playlists:
            flash('Username does not exits')
            return "FAILED"

        user_rfids[rfid] = username

        return "SUCCESS"

    @flask.route("/add_song", methods=["POST"])
    def add_song():
        username = request.form.get("username")
        hour = request.form.get("hour")
        album = request.form.get("album")
        song = request.form.get("song")

        if not username or not hour or not album or not song:
            flash('Empty username or hour or album or song')
            return "FAILED"
        if username not in shared_playlists:
            flash('User does not exits')
            return "FAILED"

        try:
            h, m = map(int, hour.split(":"))
            play_time = time(h, m)
        except:
            flash('wrong time format')
            return "FAILED"

        shared_playlists[username].append((play_time, album, song))
        playlist_update_event.set()

        return "SUCCESS"

    @flask.route("/remove_song", methods=["POST"])
    def remove_song():
        username = request.form.get("username")
        song = request.form.get("song")
        if not username or not song:
            flash('Empty username or song')
            return "FAILED"
        if username not in shared_playlists:
            flash('User does not exits')
            return "FAILED"

        playlist = shared_playlists[username]
        playlist_copy = list(playlist)

        before_count = len(playlist)

        for entry in playlist:
            if entry[2] == song:
                playlist.remove(entry)
                break

        after_count = len(shared_playlists[username])

        if before_count == after_count:
            flash('Song not found')
            return "FAILED"

        if after_count == 0:
            found = False
            for user, user_playlist in shared_playlists.items():
                if len(user_playlist) > 0:
                    found = True
                    current_user.set(user)
                    playlist_update_event.set()
                    break
            if not found:
                playlist.extend(playlist_copy)
                flash("You are trying to remove the last song in all playlists. Don't.")
                return "FAILED"
        return "SUCCESS"

    @flask.route("/change_hour", methods=["POST"])
    def change_hour():
        username = request.form.get("username")
        old_hour = request.form.get("old_hour")
        album = request.form.get("album")
        song = request.form.get("song")
        new_hour = request.form.get("new_hour")

        if not username or not album or not song or not new_hour:
            flash('Empty username or hour or song')
            return "FAILED"

        if not old_hour:
            flash("Something's wrong with the server")
            return "FAILED"

        new_hour = new_hour.split(":")
        if len(new_hour) < 2:
            flash("New hour is in wrong format")
            return "FAILED"

        try:
            new_hour = time(int(new_hour[0]), int(new_hour[1]))
        except:
            flash("New hour is in wrong format")
            return "FAILED"

        old_hour = old_hour.split(":")
        if len(old_hour) < 2:
            flash("Old hour is in wrong format")
            return "FAILED"

        try:
            old_hour = time(int(old_hour[0]), int(old_hour[1]))
        except:
            flash("Old hour is in wrong format")
            return "FAILED"

        if username not in shared_playlists:
            flash('User does not exits')
            return "FAILED"

        playlist = shared_playlists[username]

        for i, (hour, alb, sng) in enumerate(playlist):
            if hour == old_hour and alb == album and sng == song:
                playlist[i] = (new_hour, album, song)
                playlist_update_event.set()
                return "SUCCESS"

        flash('Song not found')
        return "FAILED"

    @flask.route("/change_user", methods=["POST"])
    def change_user():
        username = request.form.get("username")
        if not username:
            flash('Empty username')
            return "FAILED"

        if username not in shared_playlists:
            flash('Username does not exits')
            return "FAILED"

        if len(shared_playlists[username]) < 1:
            flash(f"{username}'s playlist is empty")
            return "FAILED"

        current_user.set(username)
        playlist_update_event.set()

        return "SUCCESS"

    flask.run(host="0.0.0.0", port=5000)

    # flask.run()


# for testing on windows
if __name__ == "__main__":
    from multiprocessing import Manager
    from main import PLAYLISTS_FILE, RFIDS_FILE
    from datetime import time
    from ctypes import c_wchar_p
    import json

    manager = Manager()
    shared_playlists = manager.dict()
    user_rfids = manager.dict()
    message_queue = Queue()
    playlist_update_event = manager.Event()
    last_read_rfid: "ValueProxy[str]" = manager.Value(c_wchar_p, "")
    user: "ValueProxy[str]" = manager.Value(c_wchar_p, "default_user")

    with open(PLAYLISTS_FILE, "r") as f:
        shared_playlists.clear()
        loaded: dict = json.load(f)
        for key, v in loaded.items():
            v: list[tuple[int, int, str, str]]
            shared_playlists[key] = manager.list([
                (time(el[0], el[1]), el[2], el[3]) for el in v])

    with open(RFIDS_FILE, "r") as f:
        user_rfids.clear()
        user_rfids.update(json.load(f))

    web_server(shared_playlists, user_rfids, message_queue,
               playlist_update_event, last_read_rfid, user, manager)

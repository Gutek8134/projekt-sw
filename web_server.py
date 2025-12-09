from multiprocessing import Queue
from multiprocessing.synchronize import Event
from multiprocessing.managers import DictProxy, ValueProxy
from datetime import time
from flask import Flask, render_template, after_this_request, Response, request, flash, redirect, url_for
from werkzeug.utils import secure_filename
import os.path

UPLOAD_FOLDER = './music'
ALLOWED_EXTENSIONS = {"mp3"}


def web_server(shared_playlists: "DictProxy[str, list[tuple[time, str, str]]]", user_rfids: "DictProxy[str, str]", message_queue: "Queue[str]", playlist_update_event: Event, last_read_rfid: ValueProxy) -> None:
    flask = Flask(__name__)
    flask.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    flask.secret_key = "secret key"

    @flask.route("/")
    def index():
        #return render_template("index.html", users=shared_playlists.keys(), playlists=shared_playlists, rfid=last_read_rfid.get())
        return render_template("index.html", users=shared_playlists.keys(), playlists=shared_playlists, rfid=last_read_rfid.value)#windows

    @flask.route("/rfid", methods=["GET"])
    def get_last_rfid():
        @after_this_request
        def add_header(response: Response):
            response.headers.add('Access-Control-Allow-Origin', '*')
            return response

        #return {"text": last_read_rfid.get()}
        return {"text": last_read_rfid.value}#windows

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
        #check if empty argument
        if not username:
            flash('Empty username')
            return "FAILED"
        #check if username exits
        if username in shared_playlists:
            flash('Username already exists')
            return "FAILED"

        shared_playlists[username] = []
        return "SUCCESS"

    @flask.route("/assign_rfid", methods=["POST"])
    def assign_rfid():
        username = request.form.get("username")
        rfid = request.form.get("rfid")

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

        before_count = len(playlist)

        shared_playlists[username] = [
            entry for entry in playlist if entry[2] != song
        ]

        after_count = len(shared_playlists[username])

        if before_count == after_count:
            flash('Song not found')
            return "FAILED"

        playlist_update_event.set()
        return "SUCCESS"

    @flask.route("/change_user", methods=["POST"])
    def change_user():
        username = request.form.get("username")
        if not username:
            flash('Empty username')
            return "FAILED"

        if username not in shared_playlists():
            flash('Username does not exits')
            return "FAILED"

        message_queue.put(f"change user {username}")

        playlist_update_event.set()

        return "SUCCESS"

    flask.run(host="0.0.0.0", port=5000, debug=True)

    #flask.run()

#for testing on windows
if __name__ == "__main__":
    from multiprocessing import Manager, Queue, Event, Value
    from datetime import time

    manager = Manager()
    shared_playlists = manager.dict()
    user_rfids = manager.dict()
    message_queue = Queue()
    playlist_update_event = Event()
    last_read_rfid = Value('i', 0)

    web_server(shared_playlists, user_rfids, message_queue, playlist_update_event, last_read_rfid)



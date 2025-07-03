import datetime as dt
from threading import Lock
from typing import Collection

from flask import Flask, request
from waitress import serve
from werkzeug.exceptions import HTTPException, UnsupportedMediaType

DEFAULT_NAME = 'chessvar-srv'
DEFAULT_HOST = '*'
DEFAULT_PORT = 58084

save_data = None
save_lock = Lock()
save_time = dt.datetime.min

app = Flask(DEFAULT_NAME)


def check_data(json_data, fields: Collection[str | tuple[str, type]] = ()):
    if not isinstance(json_data, dict):
        raise UnsupportedMediaType(description="Data must be a JSON object")
    if not fields:
        return
    for field in fields:
        if isinstance(field, tuple):
            field, field_type = field
        else:
            field_type = None
        if field not in json_data:
            raise UnsupportedMediaType(description=f"Field '{field}' is required")
        if field_type is not None and not isinstance(json_data.get(field), field_type):
            raise UnsupportedMediaType(description=f"Field '{field}' must be of type {field_type.__name__}")


@app.get('/')
def get():
    try:
        print(f"GET request received from {request.remote_addr}")
        json_data = request.get_json()
        check_data(json_data)
        time = json_data.get('time', None)
        ts = dt.datetime.min
        if time is not None:
            ts = dt.datetime.fromisoformat(time)
            ts = ts.astimezone(dt.UTC).replace(tzinfo=None)
        with save_lock:
            data = None
            if ts < save_time:
                print(f"Sending data to {request.remote_addr}")
                data = save_data
            return {
                'data': data,
                'time': save_time.replace(tzinfo=dt.UTC).isoformat(),
            }, 200
    except HTTPException as e:
        print(f"HTTP Exception: {e}")
        return {
            'error': str(e),
        }, e.code
    except Exception as e:
        print(f"Error getting data: {e}")
        return {
            'error': str(e),
        }, 500


@app.post('/')
def post():
    try:
        print(f"POST request received from {request.remote_addr}")
        json_data = request.get_json()
        check_data(json_data, ('data',))
        data = json_data.get('data', {})
        time = json_data.get('time', None)
        ts = dt.datetime.now()
        if time is not None:
            ts = dt.datetime.fromisoformat(time)
        ts = ts.astimezone(dt.UTC).replace(tzinfo=None)
        with save_lock:
            saved = False
            global save_data, save_time
            if ts > save_time:
                print(f"Storing data from {request.remote_addr}")
                save_data = data
                save_time = ts
                saved = True
            return {
                'saved': saved,
                'time': save_time.replace(tzinfo=dt.UTC).isoformat(),
            }, 200
    except HTTPException as e:
        print(f"HTTP Exception: {e}")
        return {
            'error': str(e),
        }, e.code
    except Exception as e:
        print(f"Error storing data: {e}")
        return {
            'error': str(e),
        }, 500


if __name__ == '__main__':
    print(f"Listening on {DEFAULT_HOST}:{DEFAULT_PORT}")
    serve(
        app,
        listen=f"{DEFAULT_HOST}:{DEFAULT_PORT}",
        ident=DEFAULT_NAME,
        threads=4,
    )

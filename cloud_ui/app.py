from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from functools import wraps
import sys
import os
import time
import threading

# ensure parent folder is on path so generated cloudsecurity_pb2 modules can be imported
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# gRPC stub and connection state
stub = None
grpc_channel = None
grpc_lock = threading.Lock()
GRPC_HOST = "127.0.0.1"
GRPC_PORT = 51234
GRPC_TARGET = f"{GRPC_HOST}:{GRPC_PORT}"

# how many times to try to re-create the stub on a single request before giving up
REQUEST_GRPC_RETRIES = 2
# delay between background reconnect attempts (seconds)
BACKGROUND_RECONNECT_INTERVAL = 3


def _create_stub():
    """
    Try to create and return a gRPC stub. Raises exception on failure.
    This function only creates the stub object; callers must assign it to the module-level stub.
    """
    import grpc
    import cloudsecurity_pb2_grpc  # generated file from your .proto

    MAX_MESSAGE_SIZE = 1024 * 1024 * 1024  # 1 GB

    # Add options for large messages
    channel = grpc.insecure_channel(
        GRPC_TARGET,
        options=[
            ('grpc.max_send_message_length', MAX_MESSAGE_SIZE),
            ('grpc.max_receive_message_length', MAX_MESSAGE_SIZE)
        ]
    )

    # Optionally wait for channel ready (short timeout) to fail fast if backend not up
    try:
        grpc.channel_ready_future(channel).result(timeout=1.0)
    except Exception:
        # channel not ready; still return channel+stub so we can attempt RPCs that may fail
        pass

    stub_local = cloudsecurity_pb2_grpc.UserServiceStub(channel)
    return channel, stub_local


def init_grpc(blocking=False):
    """
    Ensure module-level stub is present. If blocking=True, try once and return True/False.
    If blocking=False, will try to create stub and return True/False quickly.
    Thread-safe.
    """
    global stub, grpc_channel
    with grpc_lock:
        if stub is not None:
            return True
        try:
            channel, s = _create_stub()
            grpc_channel = channel
            stub = s
            print(f"[FLASK] gRPC stub created for {GRPC_TARGET}")
            return True
        except Exception as e:
            print(f"[FLASK] init_grpc failed: {e}")
            if blocking:
                return False
            return False


def ensure_grpc_for_request():
    """
    Called at beginning of routes that need backend. Tries a small number of times
    to create a stub (in case cloud_launcher started slightly later).
    """
    global stub
    if stub is not None:
        return True
    for _ in range(REQUEST_GRPC_RETRIES):
        if init_grpc(blocking=True):
            return True
        time.sleep(0.25)
    return False


def background_reconnect_loop():
    """
    Background thread that keeps trying to connect when Flask starts.
    This is non-blocking and safe to run in Flask dev mode.
    """
    while True:
        if stub is None:
            init_grpc(blocking=False)
        time.sleep(BACKGROUND_RECONNECT_INTERVAL)


# Start background reconnect thread (daemon so it doesn't block shutdown)
threading.Thread(target=background_reconnect_loop, daemon=True).start()


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ========== ROUTES ==========

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')

    # POST request - handle login (expects JSON body)
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({'error': 'Username and password required'}), 400

    # ensure connection to backend
    if not ensure_grpc_for_request():
        return jsonify({'error': 'Backend server not connected. Make sure cloud_launcher.py is running.'}), 500

    try:
        import cloudsecurity_pb2
        resp = stub.login(cloudsecurity_pb2.Request(login=username, password=password))
        # resp.result expected to include OTP_SENT when successful
        if "OTP_SENT" in resp.result:
            session['temp_username'] = username
            session['temp_password'] = password
            return jsonify({'success': True, 'message': 'OTP sent to your email'}), 200
        else:
            return jsonify({'error': resp.result}), 401

    except Exception as e:
        # If RPC failed, clear stub so background reconnect will attempt again
        print(f"[FLASK] login RPC error: {e}")
        with grpc_lock:
            try:
                # attempt to close channel if exists
                if grpc_channel:
                    grpc_channel.close()
            except Exception:
                pass
            # reset stub so reconnect logic can recreate it
            globals()['stub'] = None
            globals()['grpc_channel'] = None
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/otp', methods=['GET'])
def otp_page():
    if 'temp_username' not in session:
        return redirect(url_for('login'))
    return render_template('otp.html')


@app.route('/verify-otp', methods=['POST'])
def verify_otp_route():
    if 'temp_username' not in session:
        return jsonify({'error': 'Session expired. Please login again.'}), 401

    data = request.json or {}
    otp = data.get('otp', '').strip()

    if not otp or len(otp) != 6:
        return jsonify({'error': 'Please enter a 6-digit OTP'}), 400

    username = session['temp_username']

    if not ensure_grpc_for_request():
        return jsonify({'error': 'Backend server not connected.'}), 500

    try:
        import cloudsecurity_pb2
        resp = stub.verifyOtp(cloudsecurity_pb2.Request(login=username, password=otp))
        if resp.result == "AUTH_SUCCESS":
            session['username'] = username
            session.pop('temp_username', None)
            session.pop('temp_password', None)
            return jsonify({'success': True, 'message': 'Login successful!'}), 200
        else:
            return jsonify({'error': resp.result}), 401
    except Exception as e:
        print(f"[FLASK] verifyOtp RPC error: {e}")
        with grpc_lock:
            try:
                if grpc_channel:
                    grpc_channel.close()
            except Exception:
                pass
            globals()['stub'] = None
            globals()['grpc_channel'] = None
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/resend-otp', methods=['POST'])
def resend_otp_route():
    if 'temp_username' not in session:
        return jsonify({'error': 'Session expired. Please login again.'}), 401

    username = session['temp_username']
    password = session.get('temp_password', '')

    if not ensure_grpc_for_request():
        return jsonify({'error': 'Backend server not connected.'}), 500

    try:
        import cloudsecurity_pb2
        resp = stub.login(cloudsecurity_pb2.Request(login=username, password=password))
        if "OTP_SENT" in resp.result:
            return jsonify({'success': True, 'message': 'OTP resent to your email'}), 200
        else:
            return jsonify({'error': 'Failed to resend OTP'}), 400
    except Exception as e:
        print(f"[FLASK] resend OTP RPC error: {e}")
        with grpc_lock:
            try:
                if grpc_channel:
                    grpc_channel.close()
            except Exception:
                pass
            globals()['stub'] = None
            globals()['grpc_channel'] = None
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@app.route('/dashboard')
@login_required
def dashboard():
    username = session['username']
    return render_template('dashboard.html', username=username)


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 * 1024  # 1 GB
@app.route('/upload', methods=['POST'])
@login_required
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    
    username = session['username']
    
    if stub is None:
        return jsonify({'error': 'Backend server not connected'}), 500
    
    try:
        import cloudsecurity_pb2
        file_data = file.read()
        
        resp = stub.upload(cloudsecurity_pb2.UploadRequest(
            username=username,
            filename=file.filename,
            data=file_data
        ))
        
        if 'replicated' in resp.result.lower() or 'uploaded' in resp.result.lower():
            return jsonify({'success': True, 'message': resp.result}), 200
        else:
            return jsonify({'error': resp.result}), 400
    
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500

# Replace your /get-files route in app.py with this debug version



@app.route('/get-files', methods=['GET'])
@login_required
def get_files():
    username = session['username']
    print(f"\n[FLASK /get-files] Called for user: {username}")
    print(f"[FLASK /get-files] Stub exists: {stub is not None}")
    
    if stub is None:
        print(f"[FLASK /get-files] ERROR: Stub is None!")
        return jsonify({'error': 'Backend server not connected'}), 500
    
    try:
        print(f"[FLASK /get-files] Importing cloudsecurity_pb2...")
        import cloudsecurity_pb2
        print(f"[FLASK /get-files] Creating UserRequest for {username}...")
        
        user_request = cloudsecurity_pb2.UserRequest(username=username)
        print(f"[FLASK /get-files] Calling stub.listFiles()...")
        
        resp = stub.listFiles(user_request)
        print(f"[FLASK /get-files] Response received!")
        print(f"[FLASK /get-files] Response type: {type(resp)}")
        print(f"[FLASK /get-files] Filenames: {resp.filenames}")
        print(f"[FLASK /get-files] Sizes: {resp.sizes}")
        
        files = []
        for i, filename in enumerate(resp.filenames):
            files.append({
                'name': filename,
                'size': resp.sizes[i] if i < len(resp.sizes) else 0
            })
        
        print(f"[FLASK /get-files] Returning {len(files)} files")
        return jsonify({'success': True, 'files': files}), 200
    
    except Exception as e:
        print(f"[FLASK /get-files] EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Error loading files: {str(e)}'}), 500
















@app.route('/download/<filename>', methods=['GET'])
@login_required
def download(filename):
    username = session['username']
    
    if stub is None:
        return jsonify({'error': 'Backend server not connected'}), 500
    
    try:
        import cloudsecurity_pb2
        resp = stub.download(cloudsecurity_pb2.DownloadRequest(
            username=username,
            filename=filename
        ))
        
        if resp.success:
            from flask import send_file
            from io import BytesIO
            
            return send_file(
                BytesIO(resp.data),
                as_attachment=True,
                download_name=filename
            )
        else:
            return jsonify({'error': 'File not found'}), 404
    
    except Exception as e:
        return jsonify({'error': f'Download failed: {str(e)}'}), 500

@app.route('/delete/<filename>', methods=['POST'])
@login_required
def delete(filename):
    username = session['username']
    
    if stub is None:
        return jsonify({'error': 'Backend server not connected'}), 500
    
    try:
        import cloudsecurity_pb2
        resp = stub.deleteFile(cloudsecurity_pb2.DeleteRequest(
            username=username,
            filename=filename
        ))
        
        return jsonify({'success': True, 'message': resp.result}), 200
    
    except Exception as e:
        return jsonify({'error': f'Delete failed: {str(e)}'}), 500

if __name__ == '__main__':
    # Attempt an initial connection (non-blocking)
    init_grpc(blocking=False)
    # Run Flask as before
    app.run(debug=True, port=5000)



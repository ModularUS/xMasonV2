import os.path
import signal
import sys
import atexit

from flask import Flask, render_template, request, send_file
import json
import io

import matplotlib.pyplot as plt
import app.data.data_loader as data_loader
import app.models.tf_model as tf_model
import app.utils.utils as utils


app = Flask(__name__, template_folder="templates", static_folder="static")
materials = data_loader.loadMaterials()

@app.route("/", methods=["GET", "POST"])
def home():
    return render_template('home.html')

@app.route("/get", methods=["GET"])
def handleGetRequest():
    # in case to handle multiple get requests I can
    # differentiate them with this header
    type = request.headers["Type"]
    data = {}
    if type == "materials":
        data = sendMaterials()
    elif type == "default_stack":
        data = sendDefaultStack()

    # convert into JSON:
    data_json = json.dumps(data)
    return data_json

@app.route("/post", methods=["POST"])
def handlePostRequest():
    type = request.headers["Type"]
    data = request.json
    if type == "simulation_scripts":
        return processSimulationRequest(data)
    return data

# Sends the materials from the csv file to the client
def sendMaterials():
    isPiezo = [complex(x).__abs__() != 0 for x in materials["h33"]]
    #TODO send materials from csv file
    data = {
        "materials": materials.index.tolist(),
        "isPiezo": isPiezo
    }
    return data

# Used to setup a starting transducer stack when opening the website
def sendDefaultStack():
    data = {
        "materials": ["Au", "P(VDF-TrFE)", "Au", "Transfertape", "Au", "P(VDF-TrFE)", "Au"],
        "thickness": [0.2, 120, 0.2, 42, 0.2, 120, 0.2],
        "polarization": [False, True, False, False, False, False, False]
    }
    return data

def processSimulationRequest(data):
    #TODO Validate materials and send response if failed
    materials = data["materials"]
    thickness = data["thickness"]
    polarization = data["polarization"]
    connection = data["connection"]
    area = data["area"]
    start_freq = data.get("start_freq", 1)  # Default to 1 MHz
    stop_freq = data.get("stop_freq", 50)   # Default to 50 MHz

    for t in thickness:
        if t is None or t < 0.0:
            #TODO send response to client telling the input is bad
            return
    if connection is None or (connection != "parallel_alt" and connection != "parallel" and connection != "series"):
        # TODO send response to client telling the input is bad
        return
    if area is None or area <= 0.0:
        # TODO send response to client telling the input is bad
        return
    if start_freq is None or start_freq < 0:
        # TODO send response to client telling the input is bad
        return
    if stop_freq is None or stop_freq <= 0:
        # TODO send response to client telling the input is bad
        return
    if start_freq >= stop_freq:
        # TODO send response to client telling the input is bad
        return

    stack = list(zip(materials, thickness, polarization))
    return send_file(runSimulation(stack, connection, area, start_freq, stop_freq), mimetype="image/jpeg")

def runSimulation(stack, connection, area, start_freq=1, stop_freq=50):
    frequency_band = [start_freq, stop_freq]  # MHz
    results, model = tf_model.runModel(
        active_stack=stack,
        materials=materials,
        frequency_band=frequency_band,
        area=area,
        mode=connection
    )
    plot = utils.setupPlot(logarithmic=True)
    plot.plot(results["frequency"], [abs(x) for x in results["impedance"]], markersize=1, linewidth=2, color="#0050EF")
    buffer = io.BytesIO()
    plt.savefig(buffer, format='jpg')
    buffer.seek(0)
    return buffer

def cleanup_server():
    """Cleanup function to ensure server is properly shut down"""
    print("\nShutting down Flask server...")
    try:
        func = request.environ.get('werkzeug.server.shutdown')
        if func is not None:
            func()
    except:
        pass
    print("Server shutdown complete.")
    sys.exit(0)

def signal_handler(sig, frame):
    """Handle interrupt signals (Ctrl+C, termination, etc.)"""
    print(f"\nReceived signal {sig}. Initiating graceful shutdown...")
    cleanup_server()

if __name__ == "__main__":
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)  # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # Termination signal

    # Register cleanup function to run on exit
    atexit.register(lambda: print("Flask application terminated."))

    try:
        print("Starting Flask server on http://0.0.0.0:5000")
        print("Press Ctrl+C to stop the server...")
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        cleanup_server()
    except Exception as e:
        print(f"Error occurred: {e}")
        cleanup_server()

#!/usr/bin/env python
"""
Local development runner for the Flask application.
This script sets up the correct Python path and runs the application locally.
"""
import sys
import os
import signal
import atexit

# Add the project root to Python path
# Go up one level from simulation_scripts/ to get to project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Now import and run the web application
from app.main import app

def cleanup_server():
    """Cleanup function to ensure server is properly shut down"""
    print("\nShutting down Flask server...")
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
        print(f"Starting Flask application...")
        print(f"Project root: {project_root}")
        print(f"Python path: {sys.path}")
        print("Press Ctrl+C to stop the server...")
        app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
    except KeyboardInterrupt:
        cleanup_server()
    except Exception as e:
        print(f"Error occurred: {e}")
        cleanup_server()
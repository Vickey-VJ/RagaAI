import subprocess
import os
import sys
import time
import signal
from dotenv import load_dotenv

# Determine the project root directory (one level up from 'app')
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Add project root to sys.path
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Load .env file from the project root
DOTENV_PATH = os.path.join(PROJECT_ROOT, '.env')
if os.path.exists(DOTENV_PATH):
    load_dotenv(dotenv_path=DOTENV_PATH)
    print(f"Loaded .env file from: {DOTENV_PATH} for main.py")
else:   
    print(f"Warning: .env file not found at {DOTENV_PATH}. Service ports might use defaults.")

# Configuration for services
SERVICES_CONFIG = [
    ("API Service", "services/api_service.py", "API_PORT", 8000),
    ("Scraping Service", "services/scraping_service.py", "SCRAPING_SERVICE_PORT", 8001),
    ("Retriever Service", "services/retriever_service.py", "RETRIEVER_SERVICE_PORT", 8002),
    ("Language Service", "services/language_service.py", "LANGUAGE_SERVICE_PORT", 8003),
    ("Analysis Service", "services/analysis_service.py", "ANALYSIS_SERVICE_PORT", 8004),
    ("Voice Service", "services/voice_service.py", "VOICE_SERVICE_PORT", 8005),
    ("Orchestrator Service", "services/orchestrator_service.py", "ORCHESTRATOR_SERVICE_PORT", 8006),
]

processes = []

def signal_handler(sig, frame):
    print("\nShutting down all services...")
    for p_info in processes:
        print(f"Terminating {p_info['name']} (PID: {p_info['process'].pid})...")
        p_info['process'].terminate() # Send SIGTERM
    
    # Wait for processes to terminate
    for p_info in processes:
        try:
            p_info['process'].wait(timeout=5)
        except subprocess.TimeoutExpired:
            print(f"{p_info['name']} (PID: {p_info['process'].pid}) did not terminate gracefully, killing...")
            p_info['process'].kill()
        except Exception as e:
            print(f"Error waiting for {p_info['name']}: {e}")

    print("All services shut down.")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def start_services():
    print("--- Starting All Microservices ---")
    python_executable = sys.executable # Use the same python interpreter that runs main.py

    for name, script_path, port_env_var, default_port in SERVICES_CONFIG:
        port = os.getenv(port_env_var, str(default_port))
        service_script_full_path = os.path.join(PROJECT_ROOT, script_path)

        if not os.path.exists(service_script_full_path):
            print(f"Error: Service script not found at {service_script_full_path} for {name}. Skipping.")
            continue

        # We need to ensure each service can find its own modules and the 'agents' directory.
        # The services themselves handle adding PROJECT_ROOT/parent of 'services' to sys.path.
        # The key is to run them with the correct working directory or ensure Python path is set.
        # Running them from PROJECT_ROOT as cwd is a good practice.
        
        cmd = [python_executable, service_script_full_path]
        
        try:
            # Start the service
            # Using PROJECT_ROOT as cwd ensures that services can find .env and other project files correctly.
            process = subprocess.Popen(cmd, cwd=PROJECT_ROOT)
            processes.append({"name": name, "process": process, "port": port})
            print(f"Successfully started {name} on port {port} (PID: {process.pid}). Check its console for details.")
            time.sleep(2) # Give a small delay for service to initialize and print its own startup messages
        except Exception as e:
            print(f"Failed to start {name}: {e}")
            # Optionally, decide if failure to start one service should stop others.
            # For now, we'll try to start all.

    print("\n--- All services launched (or attempted). Press Ctrl+C to shut down. ---")
    
    # Keep the main script alive, periodically checking if processes are running
    try:
        while True:
            for p_info in processes:
                if p_info['process'].poll() is not None: # Check if process has terminated
                    print(f"Service {p_info['name']} (PID: {p_info['process'].pid}) has terminated unexpectedly.")
                    # Optionally, add restart logic here
            time.sleep(5) # Check every 5 seconds
    except KeyboardInterrupt: # This will be caught by the signal handler
        pass
    finally:
        # This cleanup will run if the loop exits for reasons other than SIGINT/SIGTERM
        # (e.g. an error in this script), but signal_handler is preferred.
        if any(p_info['process'].poll() is None for p_info in processes): # If any still running
             print("Exiting main.py, ensuring services are terminated...")
             signal_handler(None, None) # Trigger cleanup

if __name__ == "__main__":
    start_services()

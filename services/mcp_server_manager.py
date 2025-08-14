import subprocess
import time
import requests
from services.base_service import ServiceManager

class MCPServerManager(ServiceManager):
    """
    Manages the lifecycle of the MCP (Multi-Agent Communication Protocol) server.
    Inherits from ServiceManager to provide a standardized interface.
    """
    def __init__(self, port: int = 8089):
        super().__init__("MCP Server")
        self._port = port
        self._health_check_url = f"http://localhost:{self._port}/health"

    def start(self):
        """
        Starts the MCP server process and waits for it to become responsive.
        Raises RuntimeError if the server fails to start.
        """
        if self.is_running:
            print(f"{self.name} is already running.")
            return

        print(f"Starting {self.name} on port {self._port}...")
        try:
            # Start MCP server via npx with vision and port
            self._proc = subprocess.Popen(
                [
                    "npx", "@agent-infra/mcp-server-browser",
                    "--port", str(self._port),
                    "--vision"
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True, # Decode stdout/stderr as text
                bufsize=1, # Line-buffered output
            )
            self._is_running = True
            print(f"Process for {self.name} started (PID: {self._proc.pid}). Waiting for health check...")

            # Optional: wait for server to become responsive
            # Read stdout/stderr in a non-blocking way to see output while waiting
            start_time = time.time()
            timeout = 10 # seconds
            server_ready = False
            while time.time() - start_time < timeout:
                try:
                    # Check for "MCP server running" or similar output in stdout/stderr
                    # This can be more robust for different server types
                    # For MCP, the health endpoint is reliable.
                    r = requests.get(self._health_check_url, timeout=1) # Short timeout for health check
                    if r.status_code == 200:
                        print(f"✅ {self.name} is running and responsive on {self._health_check_url}")
                        server_ready = True
                        break
                except requests.ConnectionError:
                    pass # Server not yet up, continue waiting
                except requests.Timeout:
                    pass # Health check timed out, server might be slow
                time.sleep(0.5) # Wait before retrying

            if not server_ready:
                self.stop() # Attempt to clean up the process
                # Read any remaining output for debugging
                stdout, stderr = self._proc.communicate(timeout=1)
                raise RuntimeError(
                    f"{self.name} failed to start in time. "
                    f"STDOUT:\n{stdout}\nSTDERR:\n{stderr}"
                )
        except FileNotFoundError:
            self._is_running = False
            self._proc = None
            raise RuntimeError(
                "npx command not found. Ensure Node.js and npm are installed "
                "and npx is available in your PATH."
            )
        except Exception as e:
            self._is_running = False
            self._proc = None
            print(f"Error starting {self.name}: {e}")
            raise

    def stop(self):
        """
        Stops the MCP server process if it is running.
        Terminates the process and cleans up.
        """
        if self._proc:
            print(f"Stopping {self.name} (PID: {self._proc.pid})...")
            try:
                self._proc.terminate()
                self._proc.wait(timeout=5) # Wait for process to terminate
                print(f"✅ {self.name} stopped.")
            except subprocess.TimeoutExpired:
                print(f"❗ {self.name} did not terminate gracefully, killing it.")
                self._proc.kill()
                self._proc.wait()
            finally:
                self._proc = None
                self._is_running = False
        else:
            print(f"{self.name} is not running.")

import subprocess
import signal
import requests
import json

# Define the global variable outside the class
ollama_process = None

class OllamaEngine:
    def __init__(self, model_name='llama3.2:3b'):
        self.model_name = model_name
    
    def launch_model(self):
        """Starts the Ollama model in a subprocess."""
        global ollama_process
        if ollama_process is None:
            print(f"Starting model: {self.model_name}")
            ollama_process = subprocess.Popen(['ollama', 'run', self.model_name])
        else:
            print("Model already running.")
    
    def stop_ollama_model(self):
        """Stops the Ollama model."""
        global ollama_process
        if ollama_process:
            print("Stopping model...")
            ollama_process.send_signal(signal.SIGINT)
            ollama_process.wait()
            ollama_process = None
    
    def ask_ollama(self, prompt):
        """Sends a prompt and returns the full response (non-streaming)."""
        try:
            response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': self.model_name,
                    'messages': [{'role': 'user', 'content': prompt}]
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()['message']['content']
        except Exception as e:
            return f"[Error] {e}"
    
    def stream_ollama_response(self, prompt):
        """Streams the response from Ollama."""
        prompt2 = f" You are my personal Finance and Tax Advisor. You believe in short on point answers wich high accuracy, you are not man of many words, but are man of precise words. You tend to simplify thing while explaining anything. User says: {prompt} "

        # prompt2 = f" You are fusion of Warren Buffet and also a cool guy. You believe in short on point answers wich high accuracy, you are not man of many words, but are man of precise words. You tend to simplify thing while explaining anything. User says: {prompt} "
        # prompt2 = f"You are a hood rapper with low IQ, but otherwise you're a PhD-level expert at music. User says: {prompt}"
        try:
            response = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': self.model_name,
                    'messages': [{'role': 'user', 'content': prompt2}],
                    'stream': True
                },
                stream=True,
                timeout=60
            )
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        # Parse each line as JSON directly (no 'data:' prefix)
                        chunk_obj = json.loads(line.decode('utf-8'))
                        
                        # Check if this chunk contains content
                        if "message" in chunk_obj and "content" in chunk_obj["message"]:
                            content = chunk_obj["message"]["content"]
                            if content:  # Only yield non-empty content
                                yield content
                        
                        # Check if the response is done
                        if chunk_obj.get("done", False):
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"JSON decode error: {e}")
                        continue
                    except Exception as e:
                        print(f"Error processing chunk: {e}")
                        continue
                        
        except Exception as e:
            yield f"[Error] {e}"
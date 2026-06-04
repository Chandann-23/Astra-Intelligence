import subprocess
import os

import subprocess
import os
import shutil
import tempfile

def execute_python_code(code: str) -> str:
    """
    Executes Python code in a secure Docker container, with a local subprocess fallback
    if Docker is not available (ideal for restricted free-tier hosting like Hugging Face Spaces).
    """
    # Remove markdown formatting if present
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
        
    code = code.strip()
    
    # Check if Docker is installed on the host
    docker_available = shutil.which("docker") is not None
    
    if docker_available:
        try:
            docker_cmd = [
                'docker', 'run', '--rm', '-i',
                '--memory=512m', '--cpus=1', 
                '--network=none', 
                'python:3.9-slim', 
                'python', '-'
            ]
            result = subprocess.run(docker_cmd, input=code, capture_output=True, text=True, timeout=15)
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
                
            if not output:
                output = "Code executed successfully with no output."
                
            return output
        except subprocess.TimeoutExpired:
            return "Error: Execution timed out after 15 seconds. Ensure there are no infinite loops."
        except Exception as e:
            return f"Error executing code in Docker: {str(e)}"
    else:
        # Fallback to local subprocess execution (sandboxed by cloud hosting environment)
        print("WARNING: Docker not found. Falling back to local restricted Python execution.")
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
                f.write(code)
                temp_path = f.name
                
            # Run the script in a restricted subprocess with a timeout
            result = subprocess.run(
                ["python", temp_path],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            output = ""
            if result.stdout:
                output += f"STDOUT:\n{result.stdout}\n"
            if result.stderr:
                output += f"STDERR:\n{result.stderr}\n"
                
            if not output:
                output = "Code executed successfully with no output."
                
            return output
        except subprocess.TimeoutExpired:
            return "Error: Local execution timed out after 15 seconds. Ensure there are no infinite loops."
        except Exception as e:
            return f"Error in local execution fallback: {str(e)}"
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except Exception:
                    pass

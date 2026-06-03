import subprocess
import os

def execute_python_code(code: str) -> str:
    """
    Executes Python code in a secure, isolated Docker container.
    """
    # Remove markdown formatting if present
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
        
    code = code.strip()
        
    try:
        # Run in a secure docker container via stdin
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
        return f"Error executing code: {str(e)}"

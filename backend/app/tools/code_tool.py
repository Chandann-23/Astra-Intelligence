import tempfile
import subprocess
import os

def execute_python_code(code: str) -> str:
    """
    Executes Python code in a local subprocess and returns stdout and stderr.
    WARNING: This is a basic implementation for local/Hugging Face environments.
    In a true production environment, use E2B or Docker for secure sandboxing.
    """
    # Remove markdown formatting if present
    if code.startswith("```python"):
        code = code[9:]
    elif code.startswith("```"):
        code = code[3:]
    if code.endswith("```"):
        code = code[:-3]
        
    code = code.strip()

    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(code)
        temp_path = f.name
        
    try:
        # Run with a timeout of 15 seconds to prevent infinite loops
        result = subprocess.run(['python', temp_path], capture_output=True, text=True, timeout=15)
        
        output = ""
        if result.stdout:
            output += f"STDOUT:\n{result.stdout}\n"
        if result.stderr:
            output += f"STDERR:\n{result.stderr}\n"
            
        if not output:
            output = "Code executed successfully with no output."
            
        return output
    except subprocess.TimeoutExpired:
        return "Error: Execution timed out after 15 seconds."
    except Exception as e:
        return f"Error executing code: {str(e)}"
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

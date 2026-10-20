import os
import subprocess
import ollama

def get_project_context(project_path="."):
    context_files = ["requirements.txt", "package.json", "go.mod", "pom.xml"]
    detected_files = {}
    
    for file_name in context_files:
        full_path = os.path.join(project_path, file_name)
        if os.path.exists(full_path):
            with open(full_path, "r") as f:
                detected_files[file_name] = f.read()
                
    return detected_files

def generate_dockerfile(context, error_log=None):
    prompt = f"""You are an expert DevOps engineer. Analyze these project files and generate a valid, production-ready Dockerfile:
{context}

CRITICAL RULES FOR BASE IMAGES:
- Use official, modern, and existing Docker Hub tags (e.g., `python:3.10-slim`, `python:3.11-slim`, `node:18-alpine`).
- DO NOT use non-existent or ancient tags like `python:3.0.0` or `python:3.0`.
"""
    if error_log:
        prompt += f"\nThe previous Dockerfile build failed with this error:\n{error_log}\nFix the Dockerfile using a modern valid base image tag like `python:3.10-slim`."

    prompt += "\nIMPORTANT: Return ONLY the raw Dockerfile content inside a ```dockerfile block. Do not add explanation text."

    response = ollama.generate(
        model="qwen2.5-coder:1.5b",
        prompt=prompt
    )
    
    content = response["response"]
    if "```dockerfile" in content:
        content = content.split("```dockerfile")[1].split("```")[0]
    elif "```" in content:
        content = content.split("```")[1].split("```")[0]
        
    return content.strip()

def build_docker_image(image_name="generated-app"):
    result = subprocess.run(
        ["docker", "build", "-t", image_name, "."],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace"
    )
    return result.returncode == 0, result.stderr or result.stdout

def run_pipeline():
    print("🔍 Scanning project context...")
    context = get_project_context()
    
    if not context:
        print("❌ No standard manifest file found!")
        return

    attempts = 3
    error_log = None

    for attempt in range(1, attempts + 1):
        print(f"\n⚡ Generating Dockerfile (Attempt {attempt}/{attempts})...")
        dockerfile_content = generate_dockerfile(context, error_log)
        
        print("--- Generated Dockerfile ---")
        print(dockerfile_content)
        print("----------------------------")

        with open("Dockerfile", "w") as f:
            f.write(dockerfile_content)
            
        print("📄 Dockerfile written. Testing build with Docker...")
        success, stderr = build_docker_image()
        
        if success:
            print("✅ Docker build succeeded!")
            return
        else:
            print("❌ Docker build failed with error:")
            print(stderr)
            error_log = stderr

    print("\n🚨 Failed to resolve build errors after maximum attempts.")

if __name__ == "__main__":
    run_pipeline()
import os
import json
import subprocess
from typing import Optional, Dict, Any

def get_uploadthing_env() -> Dict[str, str]:
    env = os.environ.copy()
    token = env.get("UPLOADTHING_TOKEN", "").strip()
    secret = env.get("UPLOADTHING_SECRET", "").strip()
    app_id = env.get("UPLOADTHING_APP_ID", "").strip()
    
    if token:
        env["UPLOADTHING_TOKEN"] = token
    if secret:
        env["UPLOADTHING_SECRET"] = secret
    if app_id:
        env["UPLOADTHING_APP_ID"] = app_id
    return env

def upload_file_to_uploadthing(
    file_path: str,
    original_filename: str,
    content_type: str = "image/png"
) -> Optional[Dict[str, Any]]:
    """
    Uploads a local file to UploadThing v7 CDN using the UploadThing UTApi service.
    Returns a dictionary containing 'url', 'ufsUrl', 'key', etc. on success,
    or None on error.
    """
    if not os.path.exists(file_path):
        print(f"[UploadThing] File not found: {file_path}")
        return None

    service_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "upload_service.cjs")
    if not os.path.exists(service_script):
        print(f"[UploadThing] Service script not found at {service_script}")
        return None

    env = get_uploadthing_env()

    try:
        proc = subprocess.run(
            [
                "node",
                service_script,
                file_path,
                original_filename or "image.png",
                content_type or "image/png"
            ],
            capture_output=True,
            text=True,
            timeout=45,
            env=env
        )

        if proc.stdout:
            # Parse output lines to extract the JSON response
            for line in reversed(proc.stdout.strip().split("\n")):
                line = line.strip()
                if line.startswith("{") and line.endswith("}"):
                    try:
                        result = json.loads(line)
                        if result.get("success") and result.get("url"):
                            print(f"[UploadThing] Successfully uploaded {original_filename} -> {result['url']}")
                            return result
                        elif not result.get("success"):
                            print(f"[UploadThing] Error from service: {result.get('error')}")
                    except Exception as json_err:
                        print(f"[UploadThing] Failed to parse JSON: {json_err}, raw line: {line}")

        if proc.returncode != 0:
            print(f"[UploadThing] Node process exited with code {proc.returncode}")
            if proc.stderr:
                print(f"[UploadThing] stderr: {proc.stderr[:300]}")

    except Exception as e:
        print(f"[UploadThing] Upload exception: {e}")

    return None

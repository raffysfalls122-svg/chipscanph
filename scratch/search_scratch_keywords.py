import os

keywords = ["CameraManager", "stream_camera", "api_camera_capture", "run_ocr_matching_task", "run_image_matching_task"]

for f in os.listdir("scratch"):
    if f.endswith(".py"):
        path = os.path.join("scratch", f)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as file_obj:
                content = file_obj.read()
                matches = [k for k in keywords if k in content]
                if matches:
                    print(f"File {f} matches: {matches}")
        except Exception:
            pass

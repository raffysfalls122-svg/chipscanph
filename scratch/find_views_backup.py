import os

keywords = ["class CameraManager", "def get_cached_chips"]
found = []

for root, dirs, files in os.walk("."):
    # skip .git, __pycache__, and db.sqlite3
    if ".git" in root or "__pycache__" in root or ".uploads" in root:
        continue
    for f in files:
        if f.endswith(".py") or f.endswith(".txt") or f.endswith(".md"):
            path = os.path.join(root, f)
            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as file_obj:
                    content = file_obj.read()
                    if all(k in content for k in keywords):
                        print(f"Found match: {path}")
                        found.append((path, len(content)))
            except Exception:
                pass

print("Search complete. Found:", found)

import os

git_lost_found = r"c:\Users\Windows 11\Desktop\chipscanph\.git\lost-found\other"
print(f"lost-found exists: {os.path.exists(git_lost_found)}")

if os.path.exists(git_lost_found):
    files = os.listdir(git_lost_found)
    print(f"Number of files in lost-found/other: {len(files)}")
    matches = []
    for f in files:
        path = os.path.join(git_lost_found, f)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8', errors='ignore') as file_obj:
                    text = file_obj.read()
                    if 'executeCroppedScan' in text:
                        print(f"Matched file: {f}, Size: {os.path.getsize(path)}")
                        matches.append(path)
            except Exception as e:
                pass
    print(f"Matched {len(matches)} files.")
    if matches:
        # Sort by size (descending) so the largest (complete) file is first
        matches.sort(key=lambda x: os.path.getsize(x), reverse=True)
        best_match = matches[0]
        target_path = r"c:\Users\Windows 11\Desktop\chipscanph\scanner\templates\scanner\index.html"
        import shutil
        shutil.copy(best_match, target_path)
        print(f"Restored index.html from {best_match}")

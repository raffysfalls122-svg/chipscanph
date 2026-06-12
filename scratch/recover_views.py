import json
import os

log_path = r"C:\Users\Windows 11\.gemini\antigravity-ide\brain\fb73d434-5789-41c6-85ba-14c7c723c7a6\.system_generated\logs\transcript.jsonl"
if not os.path.exists(log_path):
    print("Log file not found.")
    exit()

print("Scanning log file...")
found_contents = []

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line in enumerate(f, 1):
        if "views.py" in line or "CameraManager" in line:
            try:
                data = json.loads(line)
                # Check inside content, tool_calls, output, or arguments
                # We look for a string that contains the key parts of views.py
                text_to_check = json.dumps(data)
                if "class CameraManager:" in text_to_check and "def get_cached_chips():" in text_to_check:
                    print(f"Found match on line {line_num}!")
                    found_contents.append(data)
            except Exception as e:
                pass

print(f"Total potential views.py matches found: {len(found_contents)}")

# Let's inspect the matches and extract the longest views.py content
for i, match in enumerate(found_contents):
    # Try to extract the raw text containing views.py
    # We look for the views.py contents that were read or displayed.
    # It might be in the step where we did view_file.
    print(f"\n--- Match {i+1} ---")
    print("Keys in match:", match.keys())
    if "type" in match:
        print("Type:", match["type"])
    if "tool_calls" in match:
        print("Has tool calls:", len(match["tool_calls"]))
    
    # We can write a parser to look for the output of views.py view_file call
    # The view_file output is typically in the "content" or "output" of the tool call result.
    # Let's search inside the match for strings of size > 50000
    def find_long_strings(obj, max_str_list):
        if isinstance(obj, str):
            if len(obj) > 30000 and "CameraManager" in obj and "get_cached_chips" in obj:
                max_str_list.append(obj)
        elif isinstance(obj, dict):
            for k, v in obj.items():
                find_long_strings(v, max_str_list)
        elif isinstance(obj, list):
            for item in obj:
                find_long_strings(item, max_str_list)

    long_strings = []
    find_long_strings(match, long_strings)
    print("Long strings found:", len(long_strings))
    if long_strings:
        # Save the longest one as recovered_views.py
        longest_str = max(long_strings, key=len)
        print("Longest string length:", len(longest_str))
        
        # Clean line numbers from view_file output if they were added (format: '123: content')
        # Let's check if it has line numbers (e.g. starts with '1: ' or has lines like '1: from django.shortcuts')
        lines = longest_str.split("\n")
        cleaned_lines = []
        has_line_numbers = any(re.match(r'^\d+:\s', l) for l in lines[:10])
        import re
        if has_line_numbers:
            print("Detected line numbers in text. Cleaning them up...")
            for l in lines:
                m = re.match(r'^\d+:\s?(.*)', l)
                if m:
                    cleaned_lines.append(m.group(1))
                else:
                    cleaned_lines.append(l)
            recovered_code = "\n".join(cleaned_lines)
        else:
            recovered_code = longest_str
            
        out_file = f"scanner/views.py"
        with open(out_file, "w", encoding="utf-8") as out_f:
            out_f.write(recovered_code)
        print(f"Successfully recovered and wrote to {out_file}!")
        break

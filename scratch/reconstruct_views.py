import json
import os
import re

log_path = r"C:\Users\Windows 11\Desktop\chipscanph\.gemini\antigravity-ide\brain\fb73d434-5789-41c6-85ba-14c7c723c7a6\.system_generated\logs\transcript.jsonl"
if not os.path.exists(log_path):
    # Try the alternative path
    log_path = r"C:\Users\Windows 11\.gemini\antigravity-ide\brain\fb73d434-5789-41c6-85ba-14c7c723c7a6\.system_generated\logs\transcript.jsonl"

print("Scanning log file for chunks...")
chunks = {}

with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
    for line_num, line_raw in enumerate(f, 1):
        try:
            data = json.loads(line_raw)
            # Check if this is a tool execution result containing views.py contents
            # We check if 'content' exists and contains lines with format 'line_number: original_line'
            content = data.get("content", "")
            if "views.py" in content and "The following code has been modified to include a line number" in content:
                # This is a view_file output!
                # Let's extract the lines
                lines = content.split("\n")
                # Find start line and end line from the first few lines of the output
                m_range = re.search(r"Showing lines (\d+) to (\d+)", content)
                if m_range:
                    start_line = int(m_range.group(1))
                    end_line = int(m_range.group(2))
                    print(f"Found chunk for lines {start_line} to {end_line} on line {line_num}!")
                    
                    # Extract code lines
                    code_lines = []
                    for l in lines:
                        # Match things like "123: code"
                        m_code = re.match(r"^(\d+):\s?(.*)", l)
                        if m_code:
                            ln = int(m_code.group(1))
                            lcontent = m_code.group(2)
                            code_lines.append((ln, lcontent))
                    
                    if code_lines:
                        chunks[(start_line, end_line)] = code_lines
        except Exception as e:
            pass

print(f"Total chunks retrieved: {len(chunks)}")

# Sort chunks and build the reconstructed file
reconstructed = {}
for (start, end), lines in sorted(chunks.items()):
    for ln, text in lines:
        reconstructed[ln] = text

# Fill in lines from 1 to the maximum line number found
max_line = max(reconstructed.keys()) if reconstructed else 0
print(f"Maximum line number found: {max_line}")

final_lines = []
missing_lines = []
for ln in range(1, max_line + 1):
    if ln in reconstructed:
        final_lines.append(reconstructed[ln])
    else:
        missing_lines.append(ln)
        final_lines.append(f"# MISSING LINE {ln}")

print(f"Missing lines: {missing_lines}")

out_path = "scanner/views.py"
with open(out_path, "w", encoding="utf-8") as out_f:
    out_f.write("\r\n".join(final_lines) + "\r\n")

print(f"Reconstructed views.py written to {out_path}!")

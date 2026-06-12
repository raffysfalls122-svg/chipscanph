import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

import re
from scanner.models import Chip

# Raw OCR input
raw_ocr_text = """SEC 240
B813
KM8F9001JM
JMR-B4B1LC"""

print("Input RAW OCR:")
print(raw_ocr_text)
print("-" * 40)

# Helper function to normalize
def normalize_code(text):
    if not text:
        return ""
    s = text.upper()
    s = re.sub(r'[\r\n\s]+', '', s)
    return re.sub(r'[^A-Z0-9]', '', s)

# Replicate views candidate functions locally for verification
def extract_chip_candidates(raw_text):
    if not raw_text:
        return []
    candidates = []
    # Split by spaces/common punctuation
    words = re.split(r'[\s,;\(\)\[\]\/\\\|]+', raw_text.upper())
    for w in words:
        # Clean prefix/suffix symbols but preserve inner dash
        w_clean = re.sub(r'^[^A-Z0-9]+|[^A-Z0-9]+$', '', w)
        w_clean = re.sub(r'[^A-Z0-9-]', '', w_clean)
        if not w_clean:
            continue
        
        # Exclude exact manufacturer name and standard code noise
        noise_exact = {"SEC", "240", "B813", "SAMSUNG", "HYNIX", "TOSHIBA", "KIOXIA", "EMMC", "UFS", "EMCP"}
        if w_clean in noise_exact:
            continue
        
        # Reject candidates starting with SEC
        if w_clean.startswith("SEC"):
            continue
            
        if w_clean.isdigit() and len(w_clean) < 5:
            continue
        if w_clean.isalpha() and len(w_clean) < 4:
            continue
            
        if 5 <= len(w_clean) <= 18:
            if w_clean not in candidates:
                candidates.append(w_clean)

    # Search inside full string for valid prefix substrings
    prefixes = ["KMD", "KMQ", "KMG", "KLM", "THGB", "H9TQ", "H9HQ", "TYDO", "TYEO", "TYRO", "KM", "KL", "TH", "H9", "MT", "SD", "TY", "KBG", "KMR"]
    for line in raw_text.split('\n'):
        line_upper = line.upper().strip()
        if not line_upper:
            continue
        for prefix in prefixes:
            pattern = re.escape(prefix) + r'[A-Z0-9-]{4,14}'
            matches = re.findall(pattern, line_upper)
            for m in matches:
                m_clean = re.sub(r'^[^A-Z0-9]+|[^A-Z0-9]+$', '', m)
                m_clean = re.sub(r'[^A-Z0-9-]', '', m_clean)
                if m_clean and len(m_clean) >= 5 and m_clean not in candidates:
                    if not m_clean.startswith("SEC"):
                        candidates.append(m_clean)
    return candidates

def score_chip_candidate(cand, raw_line="", all_chips=[]):
    score = 0
    length = len(cand)
    
    # Length score
    if 8 <= length <= 12:
        score += 15
    elif 13 <= length <= 14:
        score += 10
    elif 5 <= length < 8:
        score += 5
    elif length > 18:
        score -= 20
        
    # Alphanumeric mix
    has_letters = any(c.isalpha() for c in cand)
    has_digits = any(c.isdigit() for c in cand)
    if has_letters and has_digits:
        score += 15
    elif not has_letters:
        score -= 10
    elif not has_digits:
        score -= 10
        
    # Prefix check
    prefixes = ("KM", "KMD", "KMQ", "KMG", "KLM", "KL", "THG", "H9", "MT", "SD", "TY", "KBG", "KMR")
    if cand.startswith(prefixes):
        score += 20
    
    # Penalty for SEC
    if cand.startswith("SEC"):
        score -= 100
        
    # Database check
    cand_norm = normalize_code(cand)
    for chip in all_chips:
        norm_db = normalize_code(chip.code)
        if cand_norm == norm_db:
            score += 50
            break
        if chip.alias and cand_norm == normalize_code(chip.alias):
            score += 45
            break
        if chip.alternate_codes:
            alts = [normalize_code(c) for c in chip.alternate_codes.split(',') if c.strip()]
            if cand_norm in alts:
                score += 40
                break
        if len(cand_norm) >= 6 and len(norm_db) >= 6:
            if cand_norm in norm_db or norm_db in cand_norm:
                score += 15
    
    # OCR line match
    if raw_line and cand in raw_line.upper():
        score += 5
        
    if length > 14:
        score -= 5
        
    return score

# Run test
all_chips = list(Chip.objects.all())
extracted = extract_chip_candidates(raw_ocr_text)
print("Extracted candidates:", extracted)

candidate_sources = {}
for c in extracted:
    candidate_sources[c] = ['ocr']

# Glued code DB detection simulation
norm_combined_ocr = normalize_code(raw_ocr_text)
for chip in all_chips:
    norm_db = normalize_code(chip.code)
    if len(norm_db) >= 5 and not chip.code.upper().startswith("SEC"):
        if norm_db in norm_combined_ocr:
            if chip.code not in candidate_sources:
                candidate_sources[chip.code] = []
            if 'db_in_text' not in candidate_sources[chip.code]:
                candidate_sources[chip.code].append('db_in_text')

# Score candidates
candidate_scores = {}
for cand, sources in candidate_sources.items():
    base_score = 100
    if 'db_in_text' in sources:
        base_score = 5000
    
    heuristic = score_chip_candidate(cand, raw_line=raw_ocr_text, all_chips=all_chips)
    candidate_scores[cand] = base_score + heuristic

sorted_candidates = sorted(candidate_scores.items(), key=lambda item: item[1], reverse=True)
print("Scored candidates (sorted):")
for cand, score in sorted_candidates:
    print(f"  {cand}: {score}")

# Filter best candidate
best_candidate = "Unknown"
for cand, score in sorted_candidates:
    cand_upper = cand.upper().strip()
    if not cand_upper:
        continue
    if cand_upper.startswith("SEC"):
        continue
    if not (5 <= len(cand_upper) <= 18):
        continue
    has_letters = any(c.isalpha() for c in cand_upper)
    has_digits = any(c.isdigit() for c in cand_upper)
    if not (has_letters and has_digits):
        continue
    best_candidate = cand_upper
    break

print(f"Selected Best Candidate: {best_candidate}")

# Match DB
matched_chip = None
for cand, score in sorted_candidates:
    cand_norm = normalize_code(cand)
    for chip in all_chips:
        if cand_norm == normalize_code(chip.code):
            matched_chip = chip
            break
    if matched_chip:
        break

if matched_chip:
    print(f"Database Match Found! Code: {matched_chip.code}, Type: {matched_chip.type}, Size: {matched_chip.size}, Status: {matched_chip.status}")
else:
    print("No database match found.")

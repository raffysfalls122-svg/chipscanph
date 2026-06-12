import re

views_path = "scanner/views.py"

with open(views_path, "r", encoding="utf-8") as f:
    code = f.read()

code = code.replace("\r\n", "\n")

# Test run_ocr_matching_task match
target = "def run_ocr_matching_task(img):"
print("target in code:", target in code)

ocr_pattern = r"def run_ocr_matching_task\(img\):.*?return ocr_text_to_save"
match = re.search(ocr_pattern, code, flags=re.DOTALL)
if match:
    print("Match found!")
    print("Matched text length:", len(match.group(0)))
else:
    print("Match not found.")

# Test manual_err_block match
manual_err_block = """                        if not matched_chip:
                            best_candidate = c_clean"""
print("manual_err_block in code:", manual_err_block in code)

# Test scan_err_block match
scan_err_block = """                # Save ScanHistory entry
                history_entry = ScanHistory.objects.create(
                    code=result_obj["chip_code"],
                    grade=result_obj["grade"],
                    size=result_obj["storage"],
                    type=result_obj["type"],
                    maker=matched_chip.maker if matched_chip else 'N/A',
                    price_coded=price_coded,
                    price_noncode=price_noncode,
                    user=username,
                    status=matched_chip.status if matched_chip else 'noncode',
                    scan_status=scan_status,
                    ocr_text=ocr_text_to_save,
                    matched_chip=matched_chip
                )"""
print("scan_err_block in code:", scan_err_block in code)

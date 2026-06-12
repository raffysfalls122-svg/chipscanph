with open("scanner/views.py", "r", encoding="utf-8") as f:
    text = f.read()

replacement_code = r'''@csrf_exempt
def api_scan_image(request):
    if request.method == 'POST':
        try:
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'success': False, 'message': 'No image provided'}, status=400)

            # Accept ANY valid image file regardless of source or processing
            try:
                img = Image.open(image_file)
                # Convert to RGB if needed
                if img.mode in ('RGBA', 'LA', 'P'):
                    rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                    rgb_img.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                    img = rgb_img
                elif img.mode != 'RGB':
                    img = img.convert('RGB')
            except Exception as img_err:
                print(f"Image format error: {img_err}")
                return JsonResponse({'success': False, 'message': f'Invalid image file: {str(img_err)}'}, status=400)

            # Aggressive compression on server side
            max_dim = 800
            if img.width > max_dim or img.height > max_dim:
                img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

            # In-memory cached lookups
            all_chips = get_cached_chips()
            coded_prices, noncode_prices = get_cached_prices()

            # Manual override priority check
            manual_code = request.POST.get('corrected_code', '').strip()
            if not manual_code:
                manual_code = request.POST.get('code', '').strip()

            username = request.POST.get('user', 'Anonymous')
            image_name = image_file.name

            # Helper functions to clean / score candidates
            def clean_for_matching(text):
                if not text:
                    return ""
                return re.sub(r'[^A-Z0-9-]', '', text.upper())

            def normalize_ocr_confusions(text):
                if not text:
                    return ""
                s = clean_for_matching(text)
                replacements = {
                    'O': '0', 'Q': '0', 'D': '0',
                    'I': '1', 'L': '1',
                    'B': '8',
                    'S': '5',
                    'Z': '2',
                    'G': '6'
                }
                for char, repl in replacements.items():
                    s = s.replace(char, repl)
                return s

            def normalize_code(text):
                if not text:
                    return ""
                s = text.upper()
                s = re.sub(r'[\r\n\s]+', '', s)
                return re.sub(r'[^A-Z0-9]', '', s)

            def extract_chip_candidates(raw_text):
                if not raw_text:
                    return []
                candidates = []
                words = re.split(r'[\s,;\(\)\[\]\/\\|]+', raw_text.upper())
                for w in words:
                    w_clean = re.sub(r'^[^A-Z0-9]+|[^A-Z0-9]+$', '', w)
                    w_clean = re.sub(r'[^A-Z0-9-]', '', w_clean)
                    if not w_clean:
                        continue

                    noise_exact = {"SEC", "240", "B813", "SAMSUNG", "HYNIX", "TOSHIBA", "KIOXIA", "EMMC", "UFS", "EMCP"}
                    if w_clean in noise_exact:
                        continue
                    if w_clean.startswith("SEC"):
                        continue
                    if w_clean.isdigit() and len(w_clean) < 5:
                        continue
                    if w_clean.isalpha() and len(w_clean) < 4:
                        continue
                    if 5 <= len(w_clean) <= 18:
                        if w_clean not in candidates:
                            candidates.append(w_clean)

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

            KNOWN_CHIP_PREFIXES = ("KM", "KMD", "KMQ", "KMG", "KLM", "KL", "THG", "H9", "MT")
            WEAK_PREFIXES = ("SL", "AL", "OL", "RE", "LA", "SA")

            def score_chip_candidate(cand, raw_line=""):
                score = 0
                length = len(cand)
                if 9 <= length <= 14:
                    score += 20
                elif length == 8:
                    score += 15
                elif 5 <= length < 8:
                    score += 5
                elif length > 18:
                    score -= 20

                has_letters = any(c.isalpha() for c in cand)
                has_digits = any(c.isdigit() for c in cand)
                if has_letters and has_digits:
                    score += 15
                elif not has_letters:
                    score -= 10
                elif not has_digits:
                    score -= 10

                other_prefixes = ("SD", "TY", "KBG", "KMR")
                if cand.startswith(KNOWN_CHIP_PREFIXES):
                    score += 25
                elif cand.startswith(other_prefixes):
                    score += 10

                has_letters_start = cand and cand[0].isalpha()
                ends_alphanumeric = cand and cand[-1].isalnum()
                if has_letters_start and has_digits and ends_alphanumeric and (9 <= length <= 14):
                    score += 30

                if raw_line:
                    lines = [l.strip().upper() for l in raw_line.split('\n') if l.strip()]
                    for line in lines:
                        if cand.upper() == line:
                            score += 25
                            break
                        elif cand.upper() in line:
                            score += 5

                if cand.startswith("SEC"):
                    score -= 100

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
                if length > 14:
                    score -= 5
                return score

            # Build generator response
            def event_generator():
                # 1. Yield started event
                yield json.dumps({"event": "started"}) + "\n"

                matched_chip = None
                match_method = None
                best_candidate = "Unknown"
                rejected_candidates = []
                accepted_candidates = []
                sorted_candidates = []
                ocr_text_to_save = ""
                scan_hash = None
                image_matched_chip = None
                image_distance = None
                text_found = False
                image_found = False
                ai_status = 'disabled'
                ai_message = "AI query bypassed due to confident local match."
                ai_result = {
                    "visible_text": "",
                    "primary_chip_code": "",
                    "possible_codes": [],
                    "confidence": 0,
                    "notes": ""
                }

                if manual_code:
                    c_clean = re.sub(r'[^A-Z0-9-]', '', manual_code.upper()).strip()
                    if c_clean:
                        cand_norm = normalize_code(c_clean)
                        for chip in all_chips:
                            if cand_norm == normalize_code(chip.code) or (chip.alias and cand_norm == normalize_code(chip.alias)):
                                matched_chip = chip
                                match_method = 'manual_exact'
                                break
                            if chip.alternate_codes:
                                alts = [normalize_code(c) for c in chip.alternate_codes.split(',') if c.strip()]
                                if cand_norm in alts:
                                    matched_chip = chip
                                    match_method = 'manual_alternate'
                                    break
                        if not matched_chip:
                            best_candidate = c_clean
                        else:
                            best_candidate = matched_chip.code
                    text_found = matched_chip is not None
                    image_found = False

                    # Yield dummy image match event
                    yield json.dumps({
                        "event": "image_match",
                        "image_found": False,
                        "image_code": None,
                        "image_distance": None,
                        "scan_hash": None
                    }) + "\n"

                    # Yield text match event
                    yield json.dumps({
                        "event": "text_match",
                        "text_found": text_found,
                        "text_code": best_candidate if text_found else "Unknown",
                        "ocr_text": manual_code
                    }) + "\n"

                else:
                    # Parallel threads for OCR and Image Hash Matching
                    image_file.seek(0)
                    image_bytes = image_file.read()

                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                        future_hash = executor.submit(run_image_matching_task, img, all_chips)
                        future_ocr = executor.submit(run_ocr_matching_task, img)

                        # Submit AI task in parallel but don't wait for it unless local matching fails
                        future_ai = None
                        if getattr(settings, 'OPENROUTER_API_KEY', ''):
                            future_ai = executor.submit(run_ai_task, image_bytes, image_name, "")

                        # Wait for fast image hash matching (instant)
                        try:
                            scan_hash, image_matched_chip, image_distance = future_hash.result(timeout=0.2)
                        except Exception as e:
                            print("[IMAGE MATCH EXCEPTION]", e)
                            scan_hash, image_matched_chip, image_distance = None, None, None

                        image_found = image_matched_chip is not None
                        image_code = image_matched_chip.code if image_found else None

                        # Yield image_match progress
                        yield json.dumps({
                            "event": "image_match",
                            "image_found": image_found,
                            "image_code": image_code,
                            "image_distance": image_distance,
                            "scan_hash": scan_hash
                        }) + "\n"

                        # Check for Confident Visual Match (Hamming distance <= 10)
                        confident_visual = (image_matched_chip is not None and image_distance is not None and image_distance <= 10)

                        if confident_visual:
                            # Confident visual match found early!
                            matched_chip = image_matched_chip
                            match_method = 'visual_hash'
                            best_candidate = matched_chip.code
                            ai_status = 'skipped_confident_match'
                            ai_message = "Confident match found locally. AI query bypassed."
                            text_found = False

                            # Yield text match event as skipped
                            yield json.dumps({
                                "event": "text_match",
                                "text_found": False,
                                "text_code": "Skipped (Confident visual match found)",
                                "ocr_text": ""
                            }) + "\n"

                        else:
                            # Wait for OCR matching task to complete
                            try:
                                ocr_text_to_save = future_ocr.result()
                            except Exception as e:
                                print("[OCR EXCEPTION]", e)
                                ocr_text_to_save = ""

                            # Run OCR matching candidate logic
                            norm_combined_ocr = normalize_code(ocr_text_to_save)

                            # Direct DB match in raw OCR text first
                            for chip in all_chips:
                                norm_db = normalize_code(chip.code)
                                if len(norm_db) >= 5 and norm_db in norm_combined_ocr:
                                    matched_chip = chip
                                    match_method = 'db_code_in_ocr_text_first'
                                    break
                                if chip.alias:
                                    norm_alias = normalize_code(chip.alias)
                                    if len(norm_alias) >= 5 and norm_alias in norm_combined_ocr:
                                        matched_chip = chip
                                        match_method = 'db_alias_in_ocr_text_first'
                                        break
                                if chip.alternate_codes:
                                    found_alt = False
                                    for alt in chip.alternate_codes.split(','):
                                        norm_alt = normalize_code(alt)
                                        if len(norm_alt) >= 5 and norm_alt in norm_combined_ocr:
                                            matched_chip = chip
                                            match_method = 'db_alternate_in_ocr_text_first'
                                            found_alt = True
                                            break
                                    if found_alt:
                                        break

                            # If no direct match, score candidates
                            if not matched_chip:
                                ocr_candidates = extract_chip_candidates(ocr_text_to_save)
                                candidate_sources = {}
                                for c in ocr_candidates:
                                    if c not in candidate_sources:
                                        candidate_sources[c] = []
                                    candidate_sources[c].append('ocr')

                                for chip in all_chips:
                                    norm_db = normalize_code(chip.code)
                                    if len(norm_db) >= 5 and not chip.code.upper().startswith("SEC") and norm_db in norm_combined_ocr:
                                        if chip.code not in candidate_sources:
                                            candidate_sources[chip.code] = []
                                        if 'db_in_text' not in candidate_sources[chip.code]:
                                            candidate_sources[chip.code].append('db_in_text')
                                    if chip.alias:
                                        norm_alias = normalize_code(chip.alias)
                                        if len(norm_alias) >= 5 and not chip.alias.upper().startswith("SEC") and norm_alias in norm_combined_ocr:
                                            if chip.code not in candidate_sources:
                                                candidate_sources[chip.code] = []
                                            if 'db_in_text' not in candidate_sources[chip.code]:
                                                candidate_sources[chip.code].append('db_in_text')
                                            if chip.alias not in candidate_sources:
                                                candidate_sources[chip.alias] = []
                                            if 'db_in_text' not in candidate_sources[chip.alias]:
                                                candidate_sources[chip.alias].append('db_in_text')

                                candidate_scores = {}
                                for cand, sources in candidate_sources.items():
                                    base_score = 5000 if 'db_in_text' in sources else 100
                                    heuristic = score_chip_candidate(cand, raw_line=ocr_text_to_save)
                                    candidate_scores[cand] = base_score + heuristic

                                sorted_candidates = sorted(candidate_scores.items(), key=lambda item: item[1], reverse=True)

                                for cand, score in sorted_candidates:
                                    cand_upper = cand.upper().strip()
                                    if not cand_upper: continue
                                    cand_norm = normalize_code(cand_upper)

                                    has_db_match = False
                                    for chip in all_chips:
                                        norm_db = normalize_code(chip.code)
                                        norm_alias = normalize_code(chip.alias) if chip.alias else ""
                                        alts = [normalize_code(a) for a in chip.alternate_codes.split(',') if a.strip()] if chip.alternate_codes else []

                                        if cand_norm == norm_db or (norm_alias and cand_norm == norm_alias) or (cand_norm in alts):
                                            has_db_match = True
                                            break
                                        if len(cand_norm) >= 5 and len(norm_db) >= 5 and (cand_norm in norm_db or norm_db in cand_norm):
                                            has_db_match = True
                                            break

                                    if has_db_match:
                                        accepted_candidates.append(cand_upper)
                                        if best_candidate == "Unknown":
                                            best_candidate = cand_upper
                                        continue

                                    length = len(cand_upper)
                                    if length < 8 or length > 14 or not cand_upper.startswith(KNOWN_CHIP_PREFIXES) or cand_upper.startswith(WEAK_PREFIXES):
                                        rejected_candidates.append((cand_upper, "Prefix/length restriction"))
                                        continue

                                    has_letters = any(c.isalpha() for c in cand_upper)
                                    has_digits = any(c.isdigit() for c in cand_upper)
                                    if not (has_letters and has_digits):
                                        rejected_candidates.append((cand_upper, "No digit/letter mix"))
                                        continue

                                    digit_count = sum(1 for c in cand_upper if c.isdigit())
                                    if digit_count <= 1:
                                        rejected_candidates.append((cand_upper, "Too few digits"))
                                        continue

                                    if re.search(r'([A-Z0-9])\1\1', cand_upper):
                                        rejected_candidates.append((cand_upper, "Consecutive identical"))
                                        continue

                                    if score < 150:
                                        rejected_candidates.append((cand_upper, f"Score {score} < 150"))
                                        continue

                                    accepted_candidates.append(cand_upper)
                                    if best_candidate == "Unknown":
                                        best_candidate = cand_upper

                                if best_candidate != "Unknown":
                                    for cand, score in sorted_candidates:
                                        cand_norm = normalize_code(cand)
                                        for chip in all_chips:
                                            if cand_norm == normalize_code(chip.code):
                                                matched_chip = chip
                                                match_method = 'exact_code'
                                                break
                                            if chip.alias and cand_norm == normalize_code(chip.alias):
                                                matched_chip = chip
                                                match_method = 'exact_alias'
                                                break
                                            if chip.alternate_codes:
                                                alts = [normalize_code(c) for c in chip.alternate_codes.split(',') if c.strip()]
                                                if cand_norm in alts:
                                                    matched_chip = chip
                                                    match_method = 'exact_alternate'
                                                    break
                                        if matched_chip: break

                                    if not matched_chip:
                                        for cand, score in sorted_candidates:
                                            cand_norm = normalize_code(cand)
                                            for chip in all_chips:
                                                norm_db = normalize_code(chip.code)
                                                if len(norm_db) >= 5 and (cand_norm in norm_db or norm_db in cand_norm):
                                                    matched_chip = chip
                                                    match_method = 'candidate_db_contains'
                                                    break
                                            if matched_chip: break

                            text_matched_chip = matched_chip if match_method != 'visual_hash' else None
                            text_found = text_matched_chip is not None

                            # Yield text_match progress
                            yield json.dumps({
                                "event": "text_match",
                                "text_found": text_found,
                                "text_code": text_matched_chip.code if text_found else (best_candidate or None),
                                "ocr_text": ocr_text_to_save
                            }) + "\n"

                            confident_match = (matched_chip is not None) or (image_matched_chip is not None and image_distance is not None and image_distance <= 24)

                            # Consult AI vision only if local match fails
                            if confident_match:
                                ai_status = 'skipped_confident_match'
                                ai_message = "Confident match found locally. AI query bypassed."
                                if not matched_chip and image_matched_chip:
                                    matched_chip = image_matched_chip
                                    match_method = 'visual_hash'
                                    best_candidate = matched_chip.code
                            else:
                                if future_ai:
                                    # Yield event indicating AI has started
                                    yield json.dumps({"event": "ai_started"}) + "\n"
                                    try:
                                        ai_status, ai_result = future_ai.result()
                                    except Exception as e:
                                        print("[AI EXCEPTION]", e)
                                        ai_status = 'failed'
                                        ai_result = {}

                                    is_ai_valid = (ai_status not in ('failed_json', 'failed', 'disabled', 'unavailable'))
                                    if is_ai_valid:
                                        ai_primary = ai_result.get("primary_chip_code", "").strip()
                                        ai_possibles = [c.strip() for c in ai_result.get("possible_codes", []) if c.strip()]
                                        norm_combined_ai_visible = normalize_code(ai_result.get("visible_text", ""))

                                        for chip in all_chips:
                                            norm_db = normalize_code(chip.code)
                                            if len(norm_db) >= 5 and norm_combined_ai_visible and norm_db in norm_combined_ai_visible:
                                                matched_chip = chip
                                                match_method = 'db_code_in_ai_text_first'
                                                break
                                            if chip.alias:
                                                norm_alias = normalize_code(chip.alias)
                                                if len(norm_alias) >= 5 and norm_combined_ai_visible and norm_alias in norm_combined_ai_visible:
                                                    matched_chip = chip
                                                    match_method = 'db_alias_in_ai_text_first'
                                                    break

                                        if not matched_chip:
                                            candidates_ai = []
                                            if ai_primary:
                                                c_clean = re.sub(r'[^A-Z0-9-]', '', ai_primary.upper()).strip()
                                                if c_clean: candidates_ai.append(c_clean)
                                            for c in ai_possibles:
                                                c_clean = re.sub(r'[^A-Z0-9-]', '', c.upper()).strip()
                                                if c_clean and c_clean not in candidates_ai: candidates_ai.append(c_clean)

                                            for cand in candidates_ai:
                                                cand_norm = normalize_code(cand)
                                                for chip in all_chips:
                                                    if cand_norm == normalize_code(chip.code):
                                                        matched_chip = chip
                                                        match_method = 'ai_exact_code'
                                                        break
                                                    if chip.alias and cand_norm == normalize_code(chip.alias):
                                                        matched_chip = chip
                                                        match_method = 'ai_exact_alias'
                                                        break
                                                if matched_chip: break

                                        if matched_chip:
                                            best_candidate = matched_chip.code
                                        elif ai_primary:
                                            best_candidate = re.sub(r'[^A-Z0-9-]', '', ai_primary.upper()).strip()

                                # Fallback to image hash if text still failed
                                if not matched_chip and image_matched_chip:
                                    matched_chip = image_matched_chip
                                    match_method = 'visual_hash'
                                    best_candidate = matched_chip.code

                                text_matched_chip = matched_chip if match_method != 'visual_hash' else None
                                text_found = text_matched_chip is not None

                # Calculate score confidence rating
                ai_conf = ai_result.get("confidence", 0)
                if ai_conf > 0:
                    scan_confidence = ai_conf
                elif matched_chip:
                    best_term = ""
                    min_dist = 999
                    db_code_norm = normalize_code(matched_chip.code)
                    terms_to_test = [cand for cand, sc in sorted_candidates] if sorted_candidates else [normalize_code(best_candidate)]
                    for term in terms_to_test:
                        term_norm = normalize_code(term)
                        def get_levenshtein(a, b):
                            matrix = []
                            for i in range(len(b) + 1): matrix.append([i])
                            for j in range(len(a) + 1): matrix[0].append(j)
                            for i in range(1, len(b) + 1):
                                for j in range(1, len(a) + 1):
                                    if b[i-1] == a[j-1]:
                                        matrix[i].append(matrix[i-1][j-1])
                                    else:
                                        matrix[i].append(min(
                                            matrix[i-1][j-1] + 1,
                                            matrix[i][j-1] + 1,
                                            matrix[i-1][j] + 1
                                        ))
                            return matrix[len(b)][len(a)]
                        dist = get_levenshtein(term_norm, db_code_norm)
                        if dist < min_dist:
                            min_dist = dist
                            best_term = term_norm

                    max_len = max(len(best_term), len(db_code_norm), 1)
                    similarity = (max_len - min_dist) / max_len
                    scan_confidence = min(max(int(similarity * 100), 30), 99)
                else:
                    scan_confidence = 0

                # Match Family Chips (in-memory caching optimization)
                family_chips_data = []
                if matched_chip:
                    prefix = matched_chip.code[:3].upper()
                    count = 0
                    for x in all_chips:
                        if x.code != matched_chip.code:
                            if x.code.upper().startswith(prefix) or x.size == matched_chip.size:
                                family_chips_data.append({
                                    'code': x.code,
                                    'grade': x.grade,
                                    'size': x.size,
                                    'type': x.type,
                                    'maker': x.maker,
                                    'note': x.note,
                                    'status': x.status
                                })
                                count += 1
                                if count >= 5: break

                # Price Configurations (in-memory caching optimization)
                if matched_chip:
                    price_coded = coded_prices.get(matched_chip.grade, 0)
                    price_noncode = noncode_prices.get(matched_chip.size, 0)
                    price_coded_display = f"₱{price_coded}" if price_coded > 0 else "—"
                    price_noncode_display = f"₱{price_noncode}" if price_noncode > 0 else "—"
                else:
                    price_coded = 0
                    price_noncode = 0
                    price_coded_display = "N/A"
                    price_noncode_display = "N/A"

                # Create unified result structure
                if matched_chip:
                    result_obj = {
                        "matched": True,
                        "chip_code": matched_chip.code,
                        "type": matched_chip.type or "N/A",
                        "storage": matched_chip.size or "N/A",
                        "status": matched_chip.status or "N/A",
                        "grade": matched_chip.grade or "N/A",
                        "scan_confidence": scan_confidence,
                        "matching_family_chips": family_chips_data,
                        "coded_buying_price": price_coded_display,
                        "non_code_buying_price": price_noncode_display,
                        "alias": matched_chip.alias,
                        "alternate_codes": matched_chip.alternate_codes,
                        "note": matched_chip.note,
                        "source": "AI-assisted extraction + database verified" if ai_status == 'active' else "OCR-only extraction + database verified"
                    }
                    if ai_status == 'skipped_confident_match':
                        result_obj["source"] = "OCR-only extraction (Confident local match, AI bypassed)"
                else:
                    result_obj = {
                        "matched": False,
                        "chip_code": best_candidate,
                        "type": "N/A",
                        "storage": "N/A",
                        "status": "Unknown",
                        "grade": "N/A",
                        "scan_confidence": scan_confidence,
                        "matching_family_chips": [],
                        "coded_buying_price": "N/A",
                        "non_code_buying_price": "N/A",
                        "alias": "",
                        "alternate_codes": "",
                        "note": "",
                        "source": "AI-assisted extraction, no database match" if (ai_status not in ('failed_json', 'failed', 'disabled', 'unavailable')) else "OCR-only extraction, no database match"
                    }

                scan_status = 'MATCHED' if matched_chip else 'UNKNOWN'

                # Populate legacy chip dict
                if matched_chip:
                    legacy_chip_dict = {
                        'code': matched_chip.code,
                        'grade': matched_chip.grade,
                        'size': matched_chip.size,
                        'type': matched_chip.type,
                        'maker': matched_chip.maker,
                        'note': matched_chip.note,
                        'status': matched_chip.status,
                        'alias': matched_chip.alias,
                        'alternate_codes': matched_chip.alternate_codes,
                        'ocr_text': matched_chip.ocr_text,
                        'image_url': (settings.MEDIA_URL + matched_chip.image_path) if matched_chip.image_path else None,
                    }
                else:
                    legacy_chip_dict = {
                        'code': result_obj["chip_code"],
                        'grade': 'N/A',
                        'size': 'N/A',
                        'type': 'N/A',
                        'maker': 'N/A',
                        'note': result_obj["note"],
                        'status': 'noncode',
                        'alias': '',
                        'alternate_codes': '',
                        'ocr_text': ''
                    }

                # Save ScanHistory entry
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
                )

                # Save image attachment
                image_file.seek(0)
                history_entry.image.save(image_file.name, image_file, save=True)

                if ai_status == 'active':
                    ai_message = "AI-assisted extraction only. Final chip details are verified from the database."
                elif ai_status == 'disabled':
                    ai_message = "AI assistance disabled. Using OCR-only matching."
                elif ai_status == 'unavailable':
                    ai_message = "AI model unavailable. Check OPENROUTER_MODEL. Using OCR-only matching."
                elif ai_status == 'failed_json':
                    ai_message = "AI returned invalid response. Using OCR-only matching."
                elif ai_status == 'skipped_confident_match':
                    ai_message = "Confident match found locally. AI query bypassed."
                else:
                    ai_message = "AI request failed. Using OCR-only matching."

                # 5. Yield final_result event
                yield json.dumps({
                    "event": "final_result",
                    "success": True,
                    "extracted_text": ocr_text_to_save,
                    "code": result_obj["chip_code"],
                    "found": matched_chip is not None,
                    "scan_status": scan_status,
                    "image_url": history_entry.image.url if history_entry.image else None,
                    "ai_status": ai_status,
                    "ai_message": ai_message,
                    "source": result_obj["source"],
                    "result": result_obj,
                    "chip": legacy_chip_dict,
                    "text_found": text_found,
                    "text_code": text_matched_chip.code if text_matched_chip else (best_candidate or None),
                    "image_found": image_found,
                    "image_code": image_matched_chip.code if image_matched_chip else None,
                    "image_distance": image_distance,
                    "match_method": match_method,
                }) + "\n"

            return StreamingHttpResponse(event_generator(), content_type='text/plain')

        except Exception as e:
            import traceback
            print("SCAN ERROR:", str(e))
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)'''

start_marker = '@csrf_exempt\ndef api_scan_image(request):'
end_marker = '# ==================================================================\n# 🖼️ CHIP REFERENCE IMAGE UPLOAD ENDPOINT'

start_idx = text.find(start_marker)
end_idx = text.find(end_marker)

if start_idx != -1 and end_idx != -1:
    new_text = text[:start_idx] + replacement_code + "\n\n\n" + text[end_idx:]
    with open("scanner/views.py", "w", encoding="utf-8") as f:
        f.write(new_text)
    print("Success!")
else:
    print("Markers not found:", start_idx, end_idx)

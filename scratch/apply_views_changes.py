import re
import sys
import os

views_path = "scanner/views.py"

with open(views_path, "r", encoding="utf-8") as f:
    code = f.read()

# Normalize CRLF to LF
code = code.replace("\r\n", "\n")

# 1. Replace run_ocr_matching_task(img)
ocr_pattern = r"def run_ocr_matching_task\(img\):.*?return ocr_text_to_save"
optimized_ocr = r"""def run_ocr_matching_task(img):
    \"\"\"Fast OCR extraction - returns combined OCR text from multiple strategies\"\"\"
    from PIL import ImageOps, ImageFilter, ImageEnhance
    import concurrent.futures
    import numpy as np

    ocr_text_to_save = ""
    try:
        # Avoid aggressive downscaling. Keep high resolution up to 1200px.
        # If it's a small crop (< 600px), upscale it by 2x to make characters larger for OCR.
        img_ocr = img.copy()
        if img_ocr.width < 600 or img_ocr.height < 600:
            scale = 2
            img_ocr = img_ocr.resize((img_ocr.width * scale, img_ocr.height * scale), Image.Resampling.LANCZOS)
        elif img_ocr.width > 1200 or img_ocr.height > 1200:
            img_ocr.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

        # Convert to grayscale
        img_gray = img_ocr.convert('L')

        # Auto-invert if background is dark (mean pixel < 127)
        arr = np.array(img_gray)
        mean_pixel = np.mean(arr)
        if mean_pixel < 127:
            img_gray = ImageOps.invert(img_gray)
            arr = np.array(img_gray) # re-sync numpy array

        # Variant 1: Autocontrast + Sharpen
        img_ac = ImageOps.autocontrast(img_gray)
        img_sharp = img_ac.filter(ImageFilter.SHARPEN)

        # Variant 2: Otsu thresholding (Tesseract loves binarized images)
        # Using cv2 Otsu binarization
        import cv2
        blur_cv = cv2.GaussianBlur(arr, (3, 3), 0)
        _, otsu = cv2.threshold(blur_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        img_otsu = Image.fromarray(otsu)

        # Context-specific patch for subprocess.Popen to avoid Windows OSError [Errno 22]
        import subprocess
        class DummyStream:
            def close(self): pass
            def write(self, *args, **kwargs): pass
            def read(self, *args, **kwargs): return b''

        original_popen = subprocess.Popen
        class PatchedPopen(original_popen):
            def __init__(self, *args, **kwargs):
                if kwargs.get('stdin') == subprocess.PIPE:
                    kwargs['stdin'] = subprocess.DEVNULL
                super().__init__(*args, **kwargs)
                if self.stdin is None: self.stdin = DummyStream()
                if self.stdout is None: self.stdout = DummyStream()
                if self.stderr is None: self.stderr = DummyStream()

        subprocess.Popen = PatchedPopen
        try:
            # OEM 3 (Default Tesseract OCR Engine), char whitelist to letters, digits, hyphen
            chip_whitelist = r'--oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'

            ocr_results = []
            
            # Run Tesseract with PSM 6 and 11 on both sharp autocontrast and Otsu thresholded images
            # This covers all text styles (single line, sparse text, etc.)
            tasks = [
                (img_sharp, 6),
                (img_sharp, 11),
                (img_otsu, 6),
                (img_otsu, 11)
            ]

            with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ocr_executor:
                futures = {
                    ocr_executor.submit(run_tesseract_single, test_img, psm, chip_whitelist): (test_img, psm)
                    for test_img, psm in tasks
                }
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        for line in res.split('\n'):
                            line_stripped = line.strip()
                            if line_stripped and line_stripped not in ocr_results:
                                ocr_results.append(line_stripped)

            ocr_text_to_save = "\n".join(ocr_results)
        finally:
            subprocess.Popen = original_popen
    except Exception as ocr_err:
        print("Local OCR Error in Thread:", str(ocr_err))

    return ocr_text_to_save"""

code, count = re.subn(ocr_pattern, optimized_ocr, code, flags=re.DOTALL)
print(f"run_ocr_matching_task replaced: {count}")

# 2. Add auto-submit approvals logic inside api_scan_image (both image scanning and manual checking)
# A. For manual override check
manual_err_block = """                        if not matched_chip:
                            best_candidate = c_clean"""
manual_err_replacement = """                        if not matched_chip:
                            best_candidate = c_clean
                            # Auto submit approval request for technician if not matched
                            if username != 'admin' and username != 'Anonymous' and username != '':
                                from .models import ApprovalRequest, Notification
                                existing = ApprovalRequest.objects.filter(code=c_clean, technician=username, status='pending').first()
                                if not existing:
                                    ApprovalRequest.objects.create(
                                        code=c_clean,
                                        technician=username,
                                        status='pending',
                                        image_path=''
                                    )
                                    Notification.objects.create(
                                        user='admin',
                                        message=f"Technician {username} submitted unrecognized chip {c_clean} for approval."
                                    )"""

code, count = re.subn(re.escape(manual_err_block), manual_err_replacement, code)
print(f"manual check auto-submit approval replaced: {count}")

# B. For image scan checks (inside event_generator)
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

scan_err_replacement = """                # Save ScanHistory entry
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

                # Auto submit approval request for technician if not matched
                if not matched_chip:
                    if username != 'admin' and username != 'Anonymous' and username != '':
                        from .models import ApprovalRequest, Notification
                        existing = ApprovalRequest.objects.filter(code=result_obj["chip_code"], technician=username, status='pending').first()
                        if not existing:
                            ApprovalRequest.objects.create(
                                code=result_obj["chip_code"],
                                technician=username,
                                status='pending',
                                image_path=history_entry.image.name if history_entry.image else ''
                            )
                            Notification.objects.create(
                                user='admin',
                                message=f"Technician {username} submitted unrecognized chip {result_obj['chip_code']} for approval."
                            )"""

code, count = re.subn(re.escape(scan_err_block), scan_err_replacement, code)
print(f"image scan auto-submit approval replaced: {count}")

# 3. Add authorization checks to admin endpoints: api_chips, api_delete_chip, api_history_clear, api_users, api_delete_user
# A. api_chips POST/PUT/DELETE
api_chips_hdr = """@csrf_exempt
def api_chips(request):"""
api_chips_replacement = """@csrf_exempt
def api_chips(request):
    if request.method in ('POST', 'PUT', 'DELETE'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)"""

code, count = re.subn(re.escape(api_chips_hdr), api_chips_replacement, code)
print(f"api_chips auth check replaced: {count}")

# B. api_delete_chip POST/DELETE
api_del_chip_hdr = """@csrf_exempt
def api_delete_chip(request, code):"""
api_del_chip_replacement = """@csrf_exempt
def api_delete_chip(request, code):
    if request.method in ('POST', 'DELETE'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)"""

code, count = re.subn(re.escape(api_del_chip_hdr), api_del_chip_replacement, code)
print(f"api_delete_chip auth check replaced: {count}")

# C. api_history_clear POST
api_hist_clear_hdr = """@csrf_exempt
def api_history_clear(request):"""
api_hist_clear_replacement = """@csrf_exempt
def api_history_clear(request):
    if request.method == 'POST':
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)"""

code, count = re.subn(re.escape(api_hist_clear_hdr), api_hist_clear_replacement, code)
print(f"api_history_clear auth check replaced: {count}")

# D. api_users GET/POST
api_users_hdr = """@csrf_exempt
def api_users(request):"""
api_users_replacement = """@csrf_exempt
def api_users(request):
    if request.method in ('GET', 'POST'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)"""

code, count = re.subn(re.escape(api_users_hdr), api_users_replacement, code)
print(f"api_users auth check replaced: {count}")

# E. api_delete_user POST/DELETE
api_del_user_hdr = """@csrf_exempt
def api_delete_user(request, username):"""
api_del_user_replacement = """@csrf_exempt
def api_delete_user(request, username):
    if request.method in ('POST', 'DELETE'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)"""

code, count = re.subn(re.escape(api_del_user_hdr), api_del_user_replacement, code)
print(f"api_delete_user auth check replaced: {count}")

# 4. Append check_admin_role_helper and approvals/notifications views at the end of views.py
new_endpoints = r"""

# ==================================================================
# 🔐 ADMIN ROLE VALIDATION HELPER
# ==================================================================
def check_admin_role_helper(request):
    \"\"\"Helper to check if request is from an admin user\"\"\"
    username = None
    role = None
    try:
        # Check query parameters
        username = request.GET.get('username')
        role = request.GET.get('role')
        
        # If not in GET, check body
        if not username or not role:
            if request.body:
                data = json.loads(request.body)
                username = data.get('username') or data.get('user')
                role = data.get('role')
    except Exception:
        pass
        
    # If still not found, check request.POST
    if not username:
        username = request.POST.get('username') or request.POST.get('user')
    if not role:
        role = request.POST.get('role')
        
    if role == 'admin':
        return True
        
    if username:
        user = Technician.objects.filter(username__iexact=username).first()
        if user and user.role == 'admin':
            return True
            
    return False


# ==================================================================
# 🔔 APPROVAL & NOTIFICATION ENDPOINTS
# ==================================================================
from .models import ApprovalRequest, Notification

@csrf_exempt
def api_submit_approval(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
            username = data.get('user', '').strip()
            
            if not code or not username:
                return JsonResponse({'success': False, 'message': 'Code and user are required'}, status=400)
            
            # Check if this request is already pending
            existing = ApprovalRequest.objects.filter(code=code, technician=username, status='pending').first()
            if existing:
                return JsonResponse({'success': True, 'message': 'Request is already pending admin review'})
            
            # Find the latest ScanHistory image path for this user and code to attach
            latest_scan = ScanHistory.objects.filter(code=code, user=username).first()
            img_path = ''
            if latest_scan and latest_scan.image:
                img_path = latest_scan.image.name
            
            # Create ApprovalRequest
            req = ApprovalRequest.objects.create(
                code=code,
                technician=username,
                status='pending',
                image_path=img_path
            )
            
            # Create notification for admin
            Notification.objects.create(
                user='admin',
                message=f"Technician {username} submitted unrecognized chip {code} for approval."
            )
            
            return JsonResponse({'success': True, 'message': 'Chip submitted for admin approval.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_notifications(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username', '').strip()
            if not username:
                return JsonResponse({'success': False, 'message': 'Username is required'}, status=400)
            
            # Get notifications for this specific user or admin (if role is admin, they get 'admin' notifications)
            role = request.GET.get('role', '').strip()
            if role == 'admin' or username.lower() == 'admin':
                notifs = Notification.objects.filter(user='admin')
            else:
                notifs = Notification.objects.filter(user=username)
            
            data = [{
                'id': n.id,
                'message': n.message,
                'is_read': n.is_read,
                'created_at': str(n.created_at)
            } for n in notifs[:50]]
            
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    elif request.method == 'POST':
        # Clear or mark notifications as read
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            role = data.get('role', '').strip()
            if not username:
                return JsonResponse({'success': False, 'message': 'Username is required'}, status=400)
            
            if role == 'admin' or username.lower() == 'admin':
                Notification.objects.filter(user='admin').update(is_read=True)
            else:
                Notification.objects.filter(user=username).update(is_read=True)
                
            return JsonResponse({'success': True, 'message': 'Notifications marked as read'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_approvals_list(request):
    # Only allow admin
    if request.method == 'GET':
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
        try:
            reqs = ApprovalRequest.objects.filter(status='pending')
            data = [{
                'id': r.id,
                'code': r.code,
                'technician': r.technician,
                'status': r.status,
                'created_at': str(r.created_at),
                'image_url': settings.MEDIA_URL + r.image_path if r.image_path else None
            } for r in reqs]
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_approval_action(request, req_id):
    if not check_admin_role_helper(request):
        return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
        
    if request.method == 'POST':
        try:
            image_file = request.FILES.get('image')
            if image_file is not None:
                data = request.POST
            else:
                try:
                    data = json.loads(request.body)
                except Exception:
                    data = request.POST
                    
            action = data.get('action', '').strip().lower() # 'approve' or 'reject'
            
            req = ApprovalRequest.objects.filter(id=req_id).first()
            if not req:
                return JsonResponse({'success': False, 'message': 'Approval request not found'}, status=404)
                
            if action == 'reject':
                req.status = 'rejected'
                req.save()
                
                # Notify technician
                Notification.objects.create(
                    user=req.technician,
                    message=f"Admin rejected your request to add chip {req.code}."
                )
                return JsonResponse({'success': True, 'message': f'Request for {req.code} rejected.'})
                
            elif action == 'approve':
                size = data.get('size', '16GB')
                grade = GRADE_BY_SIZE.get(size, 'A1')
                chip_type = data.get('type', 'eMMC')
                status = data.get('status', 'coded')
                
                # Duplicate check
                if Chip.objects.filter(code__iexact=req.code).exists():
                    req.status = 'approved'
                    req.size = size
                    req.type = chip_type
                    req.classification = status
                    req.save()
                    
                    Notification.objects.create(
                        user=req.technician,
                        message=f"Admin approved your request for {req.code}. (It already exists in database)"
                    )
                    return JsonResponse({'success': True, 'message': f'Chip {req.code} already exists, request marked approved.'})
                
                # Create the chip entry
                chip = Chip.objects.create(
                    code=req.code,
                    grade=grade,
                    size=size,
                    type=chip_type,
                    status=status,
                    is_manual=True,
                    note=f"Approved technician scan request from {req.technician}"
                )
                
                # Save reference photo if provided, otherwise check if request has a scanned image to use
                if image_file is not None:
                    try:
                        save_chip_image(chip, image_file)
                    except Exception as img_err:
                        print("Approval chip image save error:", img_err)
                elif req.image_path:
                    try:
                        import shutil
                        src_abs = os.path.join(settings.MEDIA_ROOT, req.image_path.replace('/', os.sep))
                        if os.path.exists(src_abs):
                            ext = os.path.splitext(req.image_path)[1].lower() or '.jpg'
                            safe_code = re.sub(r'[^A-Z0-9._-]', '_', chip.code.upper())
                            rel_path = 'images/chips/' + safe_code + ext
                            dest_abs = os.path.join(settings.MEDIA_ROOT, rel_path.replace('/', os.sep))
                            os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
                            shutil.copy2(src_abs, dest_abs)
                            
                            chip.image_path = rel_path
                            img = Image.open(dest_abs)
                            chip.image_hash = compute_image_hash(img)
                            chip.save(update_fields=['image_path', 'image_hash'])
                    except Exception as copy_err:
                        print("Failed to copy scanned image to reference:", copy_err)
                        
                req.status = 'approved'
                req.size = size
                req.type = chip_type
                req.classification = status
                req.save()
                
                # Notify technician
                Notification.objects.create(
                    user=req.technician,
                    message=f"Admin approved your request to add chip {req.code}."
                )
                
                clear_scan_caches()
                return JsonResponse({'success': True, 'message': f'Chip {req.code} successfully approved and added to database.'})
                
            else:
                return JsonResponse({'success': False, 'message': 'Invalid action'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
"""

code += new_endpoints

# Convert line endings back to CRLF for Windows consistency
code = code.replace("\n", "\r\n")

# Write modified code back to views.py
with open(views_path, "w", encoding="utf-8") as f:
    f.write(code)

print("views.py updated successfully!")

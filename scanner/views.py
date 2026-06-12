from django.shortcuts import render
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from .models import Technician, Chip, Price, ScanHistory
import json
from django.conf import settings
import urllib.request
import base64
import os
import re
from PIL import Image
import pytesseract
import concurrent.futures
import io
import hashlib
from functools import lru_cache
import cv2
import threading
import time
import numpy as np

# Register HEIC/HEIF image formats with Pillow for iOS/iPhone camera photo uploads
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

# Caching database query results that are repeatedly called during scanning
_cache_chips = None
_cache_prices_coded_admin = None
_cache_prices_noncode_admin = None
_cache_prices_coded_tech = None
_cache_prices_noncode_tech = None

def get_cached_chips():
    global _cache_chips
    try:
        db_count = Chip.objects.count()
    except Exception:
        db_count = 0
    if _cache_chips is None or len(_cache_chips) != db_count:
        _cache_chips = list(Chip.objects.all())
    return _cache_chips

def get_cached_prices(role='tech'):
    global _cache_prices_coded_admin, _cache_prices_noncode_admin, _cache_prices_coded_tech, _cache_prices_noncode_tech
    
    try:
        db_price_count = Price.objects.count()
    except Exception:
        db_price_count = 0
        
    if (_cache_prices_coded_admin is None or _cache_prices_noncode_admin is None or 
        _cache_prices_coded_tech is None or _cache_prices_noncode_tech is None or
        db_price_count != 10):
        
        # Reload admin prices
        prices_admin = Price.objects.filter(role='admin')
        _cache_prices_coded_admin = {p.grade: p.price_coded for p in prices_admin}
        
        # Reload tech prices
        prices_tech = Price.objects.filter(role='tech')
        _cache_prices_coded_tech = {p.grade: p.price_coded for p in prices_tech}
        
        from .models import NonCodePrice
        # Reload admin noncode prices
        noncode_admin = NonCodePrice.objects.filter(role='admin')
        _cache_prices_noncode_admin = {np.size: np.price for np in noncode_admin}
        
        # Reload tech noncode prices
        noncode_tech = NonCodePrice.objects.filter(role='tech')
        _cache_prices_noncode_tech = {np.size: np.price for np in noncode_tech}

    if role == 'admin':
        return _cache_prices_coded_admin, _cache_prices_noncode_admin
    else:
        return _cache_prices_coded_tech, _cache_prices_noncode_tech

def clear_scan_caches():
    global _cache_chips, _cache_prices_coded_admin, _cache_prices_noncode_admin, _cache_prices_coded_tech, _cache_prices_noncode_tech
    _cache_chips = None
    _cache_prices_coded_admin = None
    _cache_prices_noncode_admin = None
    _cache_prices_coded_tech = None
    _cache_prices_noncode_tech = None

# Auto-locate Tesseract binary on Windows standard installation path
TESSERACT_WINDOWS_PATH = getattr(settings, 'TESSERACT_PATH', r"C:\Program Files\Tesseract-OCR\tesseract.exe")
if TESSERACT_WINDOWS_PATH and os.path.exists(TESSERACT_WINDOWS_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_WINDOWS_PATH


# ==================================================================
# 📹 SHARED LAPTOP CAMERA STREAMING (for both desktop and mobile)
# ==================================================================
camera_capture = None
camera_lock = threading.Lock()
latest_frame = None


class CameraManager:
    """Manages laptop camera access for streaming to multiple devices"""

    def __init__(self):
        self.cap = None
        self.is_running = False
        self.lock = threading.Lock()
        self.latest_frame = None
        self.frame_time = None

    def start(self):
        """Start camera capture thread"""
        if self.is_running:
            return True

        with self.lock:
            try:
                # Try to open camera (0 = default laptop camera)
                self.cap = cv2.VideoCapture(0)

                if not self.cap.isOpened():
                    print('[CAMERA] Failed to open camera device')
                    return False

                # Set camera properties for better performance
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

                self.is_running = True

                # Start background thread to read frames
                thread = threading.Thread(target=self._capture_loop, daemon=True)
                thread.start()

                print('[CAMERA] ✅ Camera started successfully')
                return True
            except Exception as e:
                print(f'[CAMERA ERROR] Failed to start camera: {e}')
                return False

    def _capture_loop(self):
        """Background thread to continuously read frames"""
        while self.is_running:
            try:
                ret, frame = self.cap.read()
                if ret:
                    with self.lock:
                        self.latest_frame = frame
                        self.frame_time = time.time()
                else:
                    print('[CAMERA] Failed to read frame')
                    break
                time.sleep(0.01)  # ~30 FPS
            except Exception as e:
                print(f'[CAMERA] Capture error: {e}')
                break

        self.is_running = False

    def get_frame(self):
        """Get latest frame as JPEG bytes"""
        with self.lock:
            if self.latest_frame is None:
                return None

            try:
                # Encode frame as JPEG
                ret, jpeg = cv2.imencode('.jpg', self.latest_frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    return jpeg.tobytes()
            except Exception as e:
                print(f'[CAMERA] Encode error: {e}')

        return None

    def capture_frame(self):
        """Capture current frame as PIL Image"""
        with self.lock:
            if self.latest_frame is None:
                return None

            try:
                # Convert BGR to RGB and then to PIL Image
                frame_rgb = cv2.cvtColor(self.latest_frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                return img
            except Exception as e:
                print(f'[CAMERA] Frame capture error: {e}')

        return None

    def stop(self):
        """Stop camera capture"""
        with self.lock:
            self.is_running = False
            if self.cap:
                self.cap.release()
                self.cap = None
        print('[CAMERA] Stopped')


# Global camera manager instance
camera_manager = CameraManager()


def stream_camera(request):
    """MJPEG stream of laptop camera - works on both desktop and mobile"""

    # Start camera if not already running
    if not camera_manager.is_running:
        if not camera_manager.start():
            return JsonResponse({'error': 'Could not access camera'}, status=500)

    def frame_generator():
        """Generate MJPEG frames"""
        while True:
            frame_bytes = camera_manager.get_frame()
            if frame_bytes is None:
                time.sleep(0.05)
                continue

            # MJPEG boundary format
            yield (b'--jpgboundary\r\n'
                   b'Content-Type: image/jpeg\r\n'
                   b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n'
                   b'Content-Disposition: inline; filename=stream.jpg\r\n\r\n' +
                   frame_bytes + b'\r\n')

            time.sleep(0.01)  # ~100 FPS max

    return StreamingHttpResponse(
        frame_generator(),
        content_type='multipart/x-mixed-replace; boundary=jpgboundary'
    )


@csrf_exempt
def api_camera_capture(request):
    """Capture frame from streaming camera - works for both desktop and mobile"""

    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Use POST'}, status=405)

    try:
        # Start camera if needed
        if not camera_manager.is_running:
            if not camera_manager.start():
                return JsonResponse({'success': False, 'message': 'Camera not available'}, status=500)

        # Capture frame
        img = camera_manager.capture_frame()
        if img is None:
            return JsonResponse({'success': False, 'message': 'Failed to capture frame'}, status=500)

        # Save to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=85)
        img_bytes.seek(0)

        # Convert to file-like object
        from django.core.files.uploadedfile import InMemoryUploadedFile
        file = InMemoryUploadedFile(
            img_bytes, None, 'camera_capture.jpg',
            'image/jpeg', img_bytes.getbuffer().nbytes, None
        )

        # Create fake request.FILES to use existing submit function
        request.FILES['image'] = file

        print('[CAMERA] Frame captured successfully')

        # Process the captured image as if it was uploaded
        return api_scan_image(request)

    except Exception as e:
        import traceback
        print(f'[CAMERA CAPTURE ERROR] {e}')
        print(traceback.format_exc())
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# ==================================================================
# 📷 ADVANCED IMAGE PREPROCESSING PIPELINE
# ==================================================================
def preprocess_image_for_ocr(pil_img):
    """Preprocess image to remove noise, glare, screen moire, skew and enhance contrast
    so that both OCR and shape-based visual matching ignore color and lighting differences."""
    try:
        # Scale up if the image is small to prevent details/text from being destroyed by downstream fixed-pixel filtering
        w, h = pil_img.size
        min_dim = 1600
        if w < min_dim or h < min_dim:
            scale = min_dim / min(w, h)
            if scale > 4.0:
                scale = 4.0
            new_w = int(w * scale)
            new_h = int(h * scale)
            pil_img = pil_img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        # Convert PIL Image to OpenCV BGR, then Grayscale
        cv_img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)

        # 1. Deskew (auto straightening text orientation)
        try:
            blur_ds = cv2.GaussianBlur(gray, (9, 9), 0)
            thresh_deskew = cv2.threshold(blur_ds, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]
            coords = np.column_stack(np.where(thresh_deskew > 0))
            if len(coords) > 50:
                angle = cv2.minAreaRect(coords)[-1]
                if angle < -45:
                    angle = -(90 + angle)
                elif angle > 45:
                    angle = 90 - angle
                else:
                    angle = -angle
                
                # Avoid rotating for extremely small or excessive skew angles
                if 0.5 < abs(angle) < 45:
                    (h, w) = gray.shape[:2]
                    center = (w // 2, h // 2)
                    M = cv2.getRotationMatrix2D(center, angle, 1.0)
                    gray = cv2.warpAffine(gray, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
        except Exception as e:
            print(f"[PREPROCESS] Deskew error: {e}")

        # 2. Descreen and Deglare (Bilateral filter + CLAHE + Median Blur)
        try:
            # Bilateral filter smooths moire grid patterns while keeping edge lines sharp
            gray = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)
        except Exception as e:
            print(f"[PREPROCESS] Bilateral filter error: {e}")

        try:
            # CLAHE enhances local contrast and removes screen glare/shadow gradients
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            gray = clahe.apply(gray)
        except Exception as e:
            print(f"[PREPROCESS] CLAHE error: {e}")

        try:
            # Median filter to clean secondary moire grids or screen pixelations
            gray = cv2.medianBlur(gray, 3)
        except Exception as e:
            print(f"[PREPROCESS] Median blur error: {e}")

        # 3. Sharpen edges (Unsharp masking filtering)
        try:
            kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            gray = cv2.filter2D(gray, -1, kernel)
        except Exception as e:
            print(f"[PREPROCESS] Sharpening error: {e}")

        # Return preprocessed image as PIL Image
        return Image.fromarray(gray).convert('RGB')
    except Exception as general_prep_err:
        print(f"[PREPROCESS GENERAL ERROR] {general_prep_err}")
        return pil_img


# ==================================================================
# 🖼️ VISUAL IMAGE MATCHING (perceptual hashing)
# OCR on physical chip surfaces is unreliable, so chips can also store a
# reference photo. We compare a scanned photo against stored photos using a
# perceptual dHash + aHash so visually-similar chips match even without OCR.
# ==================================================================
def compute_image_hash(pil_img):
    """Return a 32-char hex string = dHash(64) + aHash(64) for an image."""
    try:
        import numpy as np
        from PIL import ImageOps
        # Normalize for lighting/exposure differences between photos
        g = ImageOps.autocontrast(pil_img.convert('L'))

        # dHash: 9x8, compare each pixel to its right neighbour (horizontal gradient)
        d_img = g.resize((9, 8), Image.Resampling.LANCZOS)
        d_arr = np.asarray(d_img, dtype=np.int16)
        d_bits = (d_arr[:, 1:] > d_arr[:, :-1]).flatten()

        # aHash: 8x8, compare each pixel to the overall mean
        a_img = g.resize((8, 8), Image.Resampling.LANCZOS)
        a_arr = np.asarray(a_img, dtype=np.int16)
        a_bits = (a_arr > a_arr.mean()).flatten()

        def bits_to_hex(bits):
            value = 0
            for b in bits:
                value = (value << 1) | int(b)
            return format(value, '016x')

        return bits_to_hex(d_bits) + bits_to_hex(a_bits)
    except Exception:
        return ''


def hamming_hex(h1, h2):
    """Bit-difference count between two equal-length hex hash strings (0 = identical)."""
    if not h1 or not h2 or len(h1) != len(h2):
        return 999
    try:
        return bin(int(h1, 16) ^ int(h2, 16)).count('1')
    except Exception:
        return 999


# Fixed 1:1 grade ↔ size mapping (A1=16GB is the lowest/starting grade)
GRADE_BY_SIZE = {'16GB': 'A1', '32GB': 'A2', '64GB': 'A3', '128GB': 'A4', '256GB': 'A5'}
SIZE_BY_GRADE = {'A1': '16GB', 'A2': '32GB', 'A3': '64GB', 'A4': '128GB', 'A5': '256GB'}


def save_chip_image(chip, image_file=None, image_path_src=None):
    """Save an uploaded chip photo to MEDIA/images/chips/<CODE>.<ext> and
    preprocess + save a cleaned version alongside as <CODE>_preprocessed.png.
    Compute the image hash from the preprocessed version."""
    import io
    from PIL import Image
    
    img = None
    original_data = None
    ext = '.jpg'

    if image_file:
        image_file.seek(0)
        original_data = image_file.read()
        img = Image.open(io.BytesIO(original_data))
        if image_file.name:
            parsed_ext = os.path.splitext(image_file.name)[1].lower()
            if parsed_ext:
                ext = parsed_ext
    elif image_path_src:
        if os.path.exists(image_path_src):
            with open(image_path_src, 'rb') as f:
                original_data = f.read()
            img = Image.open(image_path_src)
            parsed_ext = os.path.splitext(image_path_src)[1].lower()
            if parsed_ext:
                ext = parsed_ext

    if not img:
        return None

    safe_code = re.sub(r'[^A-Z0-9._-]', '_', (chip.code or 'chip').upper())
    rel_path = 'images/chips/' + safe_code + ext
    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path.replace('/', os.sep))
    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, 'wb') as f:
        f.write(original_data)

    # Preprocess the reference image and save cleaned PNG version
    try:
        preprocessed_img = preprocess_image_for_ocr(img)
        preprocessed_rel_path = 'images/chips/' + safe_code + '_preprocessed.png'
        preprocessed_abs_path = os.path.join(settings.MEDIA_ROOT, preprocessed_rel_path.replace('/', os.sep))
        preprocessed_img.save(preprocessed_abs_path, format='PNG')
        
        # Compute image hash from preprocessed reference image
        chip.image_hash = compute_image_hash(preprocessed_img)
    except Exception as prep_err:
        print("Error preprocessing reference image:", prep_err)
        # Fallback: compute hash from original image
        chip.image_hash = compute_image_hash(img)

    chip.image_path = rel_path
    chip.save(update_fields=['image_hash', 'image_path'])
    return rel_path


# ==================================================================
# 📊 LAZY DATABASE PRE-SEEDER
# Checks if the database is empty on page loads and seeds default records
# ==================================================================
def seed_database_if_empty():
    from django.contrib.auth.hashers import make_password
    
    # 1. Seed/Update 'admin' credentials safely
    admin_user = Technician.objects.filter(username__iexact='admin').first()
    if not admin_user:
        Technician.objects.create(username='admin', password=make_password('admin123'), role='admin')
    else:
        # Force hash update only if currently plain-text
        if admin_user.password == 'admin123':
            admin_user.password = make_password('admin123')
            admin_user.save(update_fields=['password'])

    # 2. Seed/Update 'tech1' credentials safely
    tech_user = Technician.objects.filter(username__iexact='tech1').first()
    if not tech_user:
        Technician.objects.create(username='tech1', password=make_password('tech123'), role='tech')
    else:
        # Force hash update only if currently plain-text
        if tech_user.password == 'tech123':
            tech_user.password = make_password('tech123')
            tech_user.save(update_fields=['password'])

    # 3. Seed technician buying rates (role='tech') if empty
    if not Price.objects.filter(role='tech').exists():
        default_prices_tech = {
            'A1': 150,
            'A2': 300,
            'A3': 450,
            'A4': 650,
            'A5': 850
        }
        for grade, coded in default_prices_tech.items():
            Price.objects.create(grade=grade, price_coded=coded, price_noncode=0, role='tech')

    # 4. Seed admin monitoring rates (role='admin') if empty
    if not Price.objects.filter(role='admin').exists():
        default_prices_admin = {
            'A1': 180,
            'A2': 320,
            'A3': 480,
            'A4': 700,
            'A5': 900
        }
        for grade, coded in default_prices_admin.items():
            Price.objects.create(grade=grade, price_coded=coded, price_noncode=0, role='admin')

    # 5. Seed capacity-based Non-Code prices for tech (role='tech') if empty
    from .models import NonCodePrice
    if not NonCodePrice.objects.filter(role='tech').exists():
        default_noncode_prices_tech = {
            '16GB': 80,
            '32GB': 200,
            '64GB': 300,
            '128GB': 450,
            '256GB': 600
        }
        for size, price in default_noncode_prices_tech.items():
            NonCodePrice.objects.create(size=size, price=price, role='tech')

    # 6. Seed capacity-based Non-Code prices for admin (role='admin') if empty
    if not NonCodePrice.objects.filter(role='admin').exists():
        default_noncode_prices_admin = {
            '16GB': 90,
            '32GB': 220,
            '64GB': 330,
            '128GB': 480,
            '256GB': 650
        }
        for size, price in default_noncode_prices_admin.items():
            NonCodePrice.objects.create(size=size, price=price, role='admin')

    clear_scan_caches()


# ==================================================================
# 🌐 MAIN RENDER VIEW
# ==================================================================
from django.views.decorators.cache import never_cache

@never_cache
@ensure_csrf_cookie
def index(request):
    seed_database_if_empty()
    return render(request, 'scanner/index.html')


# ==================================================================
# 🔐 AUTH ENDPOINT
# ==================================================================
def check_password_helper(entered_pwd, stored_pwd):
    # 1. Plain text comparison
    if entered_pwd == stored_pwd:
        return True
    
    # 2. MD5 check
    try:
        import hashlib
        md5_hash = hashlib.md5(entered_pwd.encode('utf-8')).hexdigest()
        if md5_hash == stored_pwd:
            return True
    except Exception:
        pass
        
    # 3. SHA256 check
    try:
        import hashlib
        sha_hash = hashlib.sha256(entered_pwd.encode('utf-8')).hexdigest()
        if sha_hash == stored_pwd:
            return True
    except Exception:
        pass

    # 4. Django check_password (pbkdf2, bcrypt, etc.)
    try:
        from django.contrib.auth.hashers import check_password
        if check_password(entered_pwd, stored_pwd):
            return True
    except Exception:
        pass

    return False


@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            
            # Support Mock Google Login for presentation
            if data.get('is_google') is True:
                name = data.get('name', '').strip()
                age = data.get('age')
                try:
                    age_val = int(age)
                except (ValueError, TypeError):
                    return JsonResponse({'success': False, 'message': 'Age must be a valid number'}, status=400)
                
                if not name:
                    return JsonResponse({'success': False, 'message': 'Name is required'}, status=400)
                
                if age_val < 18:
                    return JsonResponse({'success': False, 'message': 'Access blocked: You must be 18 or older to use this system.'}, status=403)
                
                # Normalize name to a safe technician username
                cleaned_name = re.sub(r'[^a-zA-Z0-9_]', '', name)
                if not cleaned_name:
                    cleaned_name = f"user_{age_val}"
                
                # Fetch or create the technician record
                from django.contrib.auth.hashers import make_password
                user = Technician.objects.filter(username__iexact=cleaned_name).first()
                if not user:
                    user = Technician.objects.create(
                        username=cleaned_name,
                        password=make_password('google_mock'),
                        role='tech'
                    )
                return JsonResponse({
                    'success': True,
                    'user': {
                        'username': user.username,
                        'role': user.role
                    }
                })

            username = data.get('username', '').strip()
            password = data.get('password', '').strip()

            if not username or not password:
                return JsonResponse({'success': False, 'message': 'Username and password are required'}, status=400)

            # Extract username prefix if browser autofills an email format (e.g., admin@email.com)
            if '@' in username:
                username = username.split('@')[0]

            # Find user by username (case-insensitive)
            user = Technician.objects.filter(username__iexact=username).first()
            if user and check_password_helper(password, user.password):
                return JsonResponse({
                    'success': True,
                    'user': {
                        'username': user.username,
                        'role': user.role
                    }
                })
            return JsonResponse({'success': False, 'message': 'Invalid username or password'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 💾 CHIPS CRUD ENDPOINTS
# ==================================================================
@csrf_exempt
def api_chips(request):
    if request.method in ('POST', 'PUT', 'DELETE'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
    if request.method == 'GET':
        chips = Chip.objects.all()
        data = [{
            'code': x.code,
            'grade': x.grade,
            'size': x.size,
            'type': x.type,
            'maker': x.maker,
            'note': x.note,
            'is_manual': x.is_manual,
            'status': x.status,
            'alias': x.alias,
            'alternate_codes': x.alternate_codes,
            'ocr_text': x.ocr_text,
            'image_url': (settings.MEDIA_URL + x.image_path) if x.image_path else None,
        } for x in chips]
        return JsonResponse(data, safe=False)

    elif request.method == 'POST':
        try:
            # Support both JSON and multipart (multipart carries a reference photo)
            content_type = request.content_type or request.META.get('CONTENT_TYPE', '')
            if content_type.startswith('multipart/form-data') or 'multipart/form-data' in content_type:
                data = request.POST
                image_file = request.FILES.get('image')
            else:
                image_file = request.FILES.get('image')
                if image_file is not None:
                    data = request.POST
                else:
                    try:
                        data = json.loads(request.body)
                    except Exception:
                        data = request.POST

            raw_code = data.get('code')
            code = raw_code.strip().upper() if isinstance(raw_code, str) else ''
            
            raw_grade = data.get('grade')
            grade = raw_grade.strip() if isinstance(raw_grade, str) else 'A2'
            
            raw_size = data.get('size')
            size = raw_size.strip() if isinstance(raw_size, str) else '16GB'
            
            raw_type = data.get('type')
            chip_type = raw_type.strip() if isinstance(raw_type, str) else 'eMMC'
            
            raw_maker = data.get('maker')
            maker = raw_maker.strip() if isinstance(raw_maker, str) else ''
            
            raw_note = data.get('note')
            note = raw_note.strip() if isinstance(raw_note, str) else 'Custom entry'
            
            raw_status = data.get('status')
            status = raw_status.strip().lower() if isinstance(raw_status, str) else 'coded'
            
            raw_alias = data.get('alias')
            alias = raw_alias.strip() if isinstance(raw_alias, str) else ''
            
            raw_alt = data.get('alternate_codes')
            alternate_codes = raw_alt.strip() if isinstance(raw_alt, str) else ''
            
            raw_ocr = data.get('ocr_text')
            ocr_text = raw_ocr.strip() if isinstance(raw_ocr, str) else ''

            if not code:
                return JsonResponse({'success': False, 'message': 'Code field is required'}, status=400)

            # ── Duplicate Detection (case-insensitive, authoritative server check) ──
            if Chip.objects.filter(code__iexact=code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Duplicate chipset code detected: {code} already exists in the database.',
                    'duplicate': True
                }, status=400)

            # Enforce the 1:1 grade↔size rule (size is the source of truth)
            grade = GRADE_BY_SIZE.get(size, grade)

            chip = Chip.objects.create(
                code=code,
                grade=grade,
                size=size,
                type=chip_type,
                maker=maker,
                note=note,
                is_manual=True,
                status=status,
                alias=alias,
                alternate_codes=alternate_codes,
                ocr_text=ocr_text
            )

            # Save reference photo + preprocessed version alongside & compute hash
            image_url = None
            if image_file is not None:
                try:
                    rel = save_chip_image(chip, image_file)
                    image_url = settings.MEDIA_URL + rel
                except Exception as img_err:
                    print("Chip image save error:", str(img_err))

            clear_scan_caches()
            return JsonResponse({
                'success': True,
                'message': f'Chip {code} successfully added',
                'has_image': image_file is not None,
                'image_url': image_url
            })

        except Exception as e:
            import traceback
            print("POST CHIP ERROR:", str(e))
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    elif request.method == 'PUT':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
            chip = Chip.objects.filter(code__iexact=code).first()
            if not chip:
                return JsonResponse({'success': False, 'message': f'Chip {code} not found'}, status=404)

            chip.grade = data.get('grade', chip.grade)
            chip.size = data.get('size', chip.size)
            chip.type = data.get('type', chip.type)
            chip.maker = data.get('maker', chip.maker)
            chip.note = data.get('note', chip.note)
            chip.status = data.get('status', chip.status)
            chip.alias = data.get('alias', chip.alias)
            chip.alternate_codes = data.get('alternate_codes', chip.alternate_codes)
            chip.ocr_text = data.get('ocr_text', chip.ocr_text)
            chip.save()
            clear_scan_caches()
            return JsonResponse({'success': True, 'message': f'Chip {code} updated'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    elif request.method == 'DELETE':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
            chip = Chip.objects.filter(code__iexact=code).first()
            if not chip:
                return JsonResponse({'success': False, 'message': f'Chip {code} not found'}, status=404)
            chip.delete()
            clear_scan_caches()
            return JsonResponse({'success': True, 'message': f'Chip {code} deleted'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 📊 STATS ENDPOINT
# ==================================================================
@csrf_exempt
def api_stats(request):
    if request.method == 'GET':
        all_scans = ScanHistory.objects.all().count()
        all_techs = Technician.objects.all().count()
        coded_chips = Chip.objects.filter(status='coded').count()
        noncode_chips = Chip.objects.filter(status='noncode').count()
        manual_chips = Chip.objects.filter(is_manual=True).count()

        return JsonResponse({
            'scans': all_scans,
            'techs': all_techs,
            'coded_total': coded_chips,
            'noncode_total': noncode_chips,
            'manual_total': manual_chips
        })
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 📜 SCAN HISTORY ENDPOINT
# ==================================================================
@csrf_exempt
def api_scan_history(request):
    if request.method == 'GET':
        try:
            limit = 50
            history = list(ScanHistory.objects.all()[:limit])
            data = [{
                'id': x.id,
                'code': x.code,
                'grade': x.grade,
                'size': x.size,
                'type': x.type,
                'maker': x.maker,
                'price_coded': x.price_coded,
                'priceCoded': x.price_coded,
                'price_noncode': x.price_noncode,
                'priceNonCode': x.price_noncode,
                'timestamp': str(x.timestamp),
                'user': x.user,
                'status': x.status,
                'scan_status': x.scan_status,
                'image_url': x.image.url if x.image else None
            } for x in history]
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 🖼️ OPTIMIZED IMAGE MATCHING (runs in parallel during scan)
# ==================================================================
def run_image_matching_task(img, all_chips):
    """Rotation-invariant fast perceptual hash matching - returns scan_hash, matched_chip, distance"""
    try:
        scan_hash = compute_image_hash(img)
    except Exception:
        scan_hash = None

    image_matched_chip = None
    image_distance = None
    
    # Generate hashes for all 4 orthogonal rotations (0, 90, 180, 270 degrees)
    hashes = []
    if scan_hash:
        hashes.append(scan_hash)
    for angle in [90, 180, 270]:
        try:
            r_img = img.rotate(angle, expand=True)
            h = compute_image_hash(r_img)
            if h:
                hashes.append(h)
        except Exception:
            pass

    if hashes:
        best_img_chip, best_dist = None, 999
        for c in all_chips:
            if c.image_hash:
                # Compare each rotation hash against the database preprocessed reference image hash
                for h in hashes:
                    d = hamming_hex(h, c.image_hash)
                    if d < best_dist:
                        best_dist, best_img_chip = d, c
        if best_img_chip and best_dist <= 24:
            image_matched_chip = best_img_chip
            image_distance = best_dist

    return scan_hash, image_matched_chip, image_distance


# ==================================================================
# 📝 OPTIMIZED OCR PROCESSING WITH CONFIDENCE AND ROTATIONS
# ==================================================================
def run_tesseract_with_conf(pil_img, psm, config, min_conf=65):
    """Executes OCR and filters tokens that fall below a confidence threshold (min_conf=65)"""
    try:
        d = pytesseract.image_to_data(pil_img, config=f'--psm {psm} {config}', output_type=pytesseract.Output.DICT)
        n_boxes = len(d['text'])
        lines = {}
        for i in range(n_boxes):
            conf_val = d['conf'][i]
            try:
                conf = float(conf_val)
            except (ValueError, TypeError):
                conf = -1.0
            
            text = d['text'][i].strip()
            # Enforce confidence threshold and valid alphanumeric code tokens
            if conf >= min_conf and text:
                line_idx = d['line_num'][i]
                if line_idx not in lines:
                    lines[line_idx] = []
                lines[line_idx].append(text)
        
        result_lines = []
        for idx in sorted(lines.keys()):
            result_lines.append(" ".join(lines[idx]))
        return "\n".join(result_lines)
    except Exception as e:
        print(f"[TESSERACT CONF ERROR] {e}")
        try:
            return pytesseract.image_to_string(pil_img, config=f'--psm {psm} {config}').strip()
        except Exception:
            return ""


def run_ocr_matching_task(img, all_chips=None):
    """Fast OCR extraction - runs multiple OCR passes progressively.
    If an exact match in the database or a blocklisted keyword is found in the first
    fast pass, we return immediately to optimize performance and prevent delays."""
    from PIL import ImageOps, ImageFilter
    import concurrent.futures
    import numpy as np
    import cv2

    ocr_results = []
    try:
        # Recognize only uppercase letters, numbers, and hyphens (standard chip codes)
        chip_whitelist = r'--oem 3 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'

        # Preprocess background contrast alignment (gray + auto-invert if background is dark)
        img_gray = img.convert('L')
        arr = np.array(img_gray)
        mean_pixel = np.mean(arr)
        if mean_pixel < 127:
            img_gray = ImageOps.invert(img_gray)
            arr = np.array(img_gray)

        # Base orientation preprocessed image
        img_ac = ImageOps.autocontrast(img_gray)
        img_sharp = img_ac.filter(ImageFilter.SHARPEN)

        # Windows subprocess patching to prevent Popen OSError [Errno 22] in threads
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
            # ── PROGRESSIVE PASS 1: Base preprocessed image (highly likely correct orientation) ──
            base_txt = run_tesseract_with_conf(img_sharp, 6, chip_whitelist, 65)
            if base_txt:
                for line in base_txt.split('\n'):
                    line_stripped = line.strip()
                    if line_stripped and line_stripped not in ocr_results:
                        ocr_results.append(line_stripped)

            # Check if any candidate from Pass 1 is a direct match or blocklisted
            if ocr_results and all_chips:
                def norm_code(t):
                    s = t.upper()
                    s = re.sub(r'[\r\n\s]+', '', s)
                    return re.sub(r'[^A-Z0-9]', '', s)
                
                block_pattern = re.compile(r'^(K4E|K4F|H9HK|H9HN|PM|QualcommPM|SNAP|HELI|KIR|EXYN|SM|SDM|MT|MSM|HELIO|EXYNOS|KIRIN)', re.IGNORECASE)
                
                for cand in ocr_results:
                    cand_norm = norm_code(cand)
                    if block_pattern.match(cand_norm):
                        return "\n".join(ocr_results) # Blocklist trigger, return early!
                    
                    for chip in all_chips:
                        if cand_norm == norm_code(chip.code) or (chip.alias and cand_norm == norm_code(chip.alias)):
                            return "\n".join(ocr_results)
                        if chip.alternate_codes:
                            alts = [norm_code(c) for c in chip.alternate_codes.split(',') if c.strip()]
                            if cand_norm in alts:
                                return "\n".join(ocr_results)

            # ── PROGRESSIVE PASS 2: Rotational and scale variants (only run if Pass 1 wasn't a match) ──
            tasks = []
            
            blur_cv = cv2.GaussianBlur(arr, (3, 3), 0)
            _, otsu = cv2.threshold(blur_cv, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            img_otsu = Image.fromarray(otsu)

            # Scale variants
            tasks.append((img_sharp, 11))
            tasks.append((img_otsu, 6))
            tasks.append((img_otsu, 11))

            for scale in [1.5, 2.0]:
                for base_img in [img_sharp, img_otsu]:
                    w, h = base_img.size
                    scaled_img = base_img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)
                    tasks.append((scaled_img, 6))
                    tasks.append((scaled_img, 11))

            # Rotational variants
            for angle in [90, 180, 270]:
                for base_img in [img_sharp, img_otsu]:
                    w, h = base_img.size
                    scaled_img = base_img.resize((int(w * 1.5), int(h * 1.5)), Image.Resampling.LANCZOS)
                    rot_img = scaled_img.rotate(angle, expand=True)
                    tasks.append((rot_img, 6))
                    tasks.append((rot_img, 11))

            with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ocr_executor:
                futures = {
                    ocr_executor.submit(run_tesseract_with_conf, test_img, psm, chip_whitelist, 65): (test_img, psm)
                    for test_img, psm in tasks
                }
                for future in concurrent.futures.as_completed(futures):
                    res = future.result()
                    if res:
                        for line in res.split('\n'):
                            line_stripped = line.strip()
                            if line_stripped and line_stripped not in ocr_results:
                                ocr_results.append(line_stripped)
        finally:
            subprocess.Popen = original_popen

    except Exception as ocr_err:
        print("Local OCR Error in Thread:", str(ocr_err))

    return "\n".join(ocr_results)


# AI vision completely disabled from scanner system.


# ==================================================================
# 🖼️ PRIMARY SCAN ENDPOINT - Optimized for Mobile & Desktop
# ==================================================================
@csrf_exempt
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

            # Apply automatic image preprocessing pipeline (Grayscale, CLAHE, Bilateral filters, Sharpening, Deskew)
            img = preprocess_image_for_ocr(img)

            # Max dimension limits to preserve server CPU while keeping markings legible
            max_dim = 1600
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
                ai_message = 'AI vision completely disabled.'
                ai_result = {
                    "visible_text": "",
                    "primary_chip_code": "",
                    "possible_codes": [],
                    "confidence": 0,
                    "notes": "AI vision completely disabled."
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
                            # Auto submit approval request for technician if not matched and code is not Unknown
                            if username != 'admin' and username != 'Anonymous' and username != '' and c_clean.upper() != 'UNKNOWN':
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
                                    )
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

                    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                        future_hash = executor.submit(run_image_matching_task, img, all_chips)
                        future_ocr = executor.submit(run_ocr_matching_task, img, all_chips)

                        # Wait for fast image hash matching (instant)
                        try:
                            scan_hash, image_matched_chip, image_distance = future_hash.result(timeout=0.2)
                        except Exception as e:
                            print("[IMAGE MATCH EXCEPTION]", e)
                            scan_hash, image_matched_chip, image_distance = None, None, None

                        image_found = image_matched_chip is not None
                        image_code = image_matched_chip.code if image_found else None

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
                            text_found = False

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

                            # Fallback to image hash if text still failed
                            if not matched_chip and image_matched_chip:
                                matched_chip = image_matched_chip
                                match_method = 'visual_hash'
                                best_candidate = matched_chip.code

                            text_matched_chip = matched_chip if match_method != 'visual_hash' else None
                            text_found = text_matched_chip is not None

                            yield json.dumps({
                                "event": "text_match",
                                "text_found": text_found,
                                "text_code": text_matched_chip.code if text_found else (best_candidate or None),
                                "ocr_text": ocr_text_to_save
                            }) + "\n"

                # Calculate score confidence rating
                if matched_chip:
                    text_found = (match_method != 'visual_hash')

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
                        "source": "OCR-only extraction + database verified"
                    }
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
                        "source": "OCR-only extraction, no database match"
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

                # Auto submit approval request for technician if not matched and the code is not Unknown
                if not matched_chip and result_obj["chip_code"] and result_obj["chip_code"].upper() != 'UNKNOWN':
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
                            )

                ai_message = "AI assistance disabled. Using OCR-only matching."

                # Find fuzzy matches if not found
                fuzzy_matches = []
                if not matched_chip:
                    best_cand_norm = normalize_code(best_candidate) if best_candidate else ""
                    if best_cand_norm and best_cand_norm != 'UNKNOWN':
                        for chip in all_chips:
                            chip_norm = normalize_code(chip.code)
                            # Compute Levenshtein distance
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
                            
                            dist = get_levenshtein(best_cand_norm, chip_norm)
                            if dist <= 3:
                                fuzzy_matches.append({
                                    'code': chip.code,
                                    'size': chip.size,
                                    'grade': chip.grade,
                                    'type': chip.type
                                })
                                if len(fuzzy_matches) >= 3:
                                    break

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
                    "fuzzy_matches": fuzzy_matches,
                }) + "\n"

            return StreamingHttpResponse(event_generator(), content_type='text/plain')

        except Exception as e:
            import traceback
            print("SCAN ERROR:", str(e))
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 🖼️ CHIP REFERENCE IMAGE UPLOAD ENDPOINT
# Accepts a chip code + image file, computes pHash, saves both to the Chip.
# ==================================================================
@csrf_exempt
def api_chip_upload_image(request, code):
    if request.method == 'POST':
        try:
            chip = Chip.objects.filter(code__iexact=code).first()
            if not chip:
                return JsonResponse({'success': False, 'message': f'Chip {code} not found'}, status=404)

            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({'success': False, 'message': 'No image file provided'}, status=400)

            # Save to images/chips/<CODE> + store relative path + perceptual hash
            rel = save_chip_image(chip, image_file)
            clear_scan_caches()

            return JsonResponse({
                'success': True,
                'message': f'Reference image saved for {chip.code}',
                'image_url': settings.MEDIA_URL + rel,
                'image_hash': chip.image_hash
            })
        except Exception as e:
            import traceback
            print("IMAGE UPLOAD ERROR:", str(e))
            print(traceback.format_exc())
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 💰 PRICING ENDPOINTS (GET/POST)
# ==================================================================
@csrf_exempt
def api_prices(request):
    from .models import NonCodePrice
    if request.method == 'GET':
        try:
            role = request.GET.get('role', 'tech').strip().lower()
            if role not in ('admin', 'tech'):
                role = 'tech'
            coded_prices, noncode_prices = get_cached_prices(role)
            return JsonResponse({
                'coded': coded_prices,
                'noncode': noncode_prices
            })
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            role = data.get('role', 'tech').strip().lower()
            if role == 'admin':
                return JsonResponse({'success': False, 'message': 'Admin pricing configuration is read-only.'}, status=403)
            
            coded = data.get('coded', {})
            noncode = data.get('noncode', {})
            
            for grade, price in coded.items():
                Price.objects.update_or_create(grade=grade, role='tech', defaults={'price_coded': int(price)})
                
            for size, price in noncode.items():
                NonCodePrice.objects.update_or_create(size=size, role='tech', defaults={'price': int(price)})
                
            clear_scan_caches()
            return JsonResponse({'success': True, 'message': 'Technician prices successfully updated'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 🕘 SCAN HISTORY ENDPOINTS (GET/POST)
# ==================================================================
@csrf_exempt
def api_history(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username', '')
            role = request.GET.get('role', '')
            
            if role == 'admin':
                history = ScanHistory.objects.all()[:100]
            elif username:
                history = ScanHistory.objects.filter(user=username)[:100]
            else:
                history = ScanHistory.objects.all()[:100]
                
            data = [{
                'id': x.id,
                'code': x.code,
                'grade': x.grade,
                'size': x.size,
                'type': x.type,
                'maker': x.maker,
                'price_coded': x.price_coded,
                'priceCoded': x.price_coded,
                'price_noncode': x.price_noncode,
                'priceNonCode': x.price_noncode,
                'timestamp': str(x.timestamp),
                'user': x.user,
                'status': x.status,
                'scan_status': x.scan_status,
                'image_url': x.image.url if x.image else None
            } for x in history]
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
            username = data.get('user', 'Anonymous').strip()
            status = data.get('status', 'coded').strip().lower()
            
            all_chips = get_cached_chips()
            matched_chip = None
            cand_norm = normalize_code_helper(code)
            
            for chip in all_chips:
                if cand_norm == normalize_code_helper(chip.code) or (chip.alias and cand_norm == normalize_code_helper(chip.alias)):
                    matched_chip = chip
                    break
                if chip.alternate_codes:
                    alts = [normalize_code_helper(c) for c in chip.alternate_codes.split(',') if c.strip()]
                    if cand_norm in alts:
                        matched_chip = chip
                        break
                        
            coded_prices, noncode_prices = get_cached_prices()
            
            if matched_chip:
                grade = matched_chip.grade
                size = matched_chip.size
                type_val = matched_chip.type
                maker = matched_chip.maker or 'N/A'
                price_coded = coded_prices.get(grade, 0)
                price_noncode = noncode_prices.get(size, 0)
                scan_status = 'MATCHED'
                status = matched_chip.status
            else:
                grade = 'N/A'
                size = 'N/A'
                type_val = 'N/A'
                maker = 'N/A'
                price_coded = 0
                price_noncode = 0
                scan_status = 'UNKNOWN'
                
            entry = ScanHistory.objects.create(
                code=code,
                grade=grade,
                size=size,
                type=type_val,
                maker=maker,
                price_coded=price_coded,
                price_noncode=price_noncode,
                user=username,
                status=status,
                scan_status=scan_status,
                matched_chip=matched_chip
            )
            
            return JsonResponse({'success': True, 'message': 'Scan history entry created successfully'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_history_clear(request):
    if request.method == 'POST':
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
    if request.method == 'POST':
        try:
            username = None
            role = None
            if request.body:
                try:
                    data = json.loads(request.body)
                    username = data.get('username')
                    role = data.get('role')
                except Exception:
                    pass
            
            if not username:
                username = request.POST.get('username')
            if not role:
                role = request.POST.get('role')
                
            if role == 'admin':
                ScanHistory.objects.all().delete()
            elif username:
                ScanHistory.objects.filter(user=username).delete()
            else:
                ScanHistory.objects.all().delete()
                
            return JsonResponse({'success': True, 'message': 'Scan history cleared'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 📦 CHIPS MANAGEMENT ENDPOINTS
# ==================================================================
@csrf_exempt
def api_delete_chip(request, code):
    if request.method in ('POST', 'DELETE'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
    if request.method in ('POST', 'DELETE'):
        try:
            chip = Chip.objects.filter(code__iexact=code).first()
            if not chip:
                return JsonResponse({'success': False, 'message': f'Chip {code} not found'}, status=404)
            chip.delete()
            clear_scan_caches()
            return JsonResponse({'success': True, 'message': f'Chip {code} successfully deleted'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_check_chip(request, code):
    if request.method == 'GET':
        try:
            clear_scan_caches()
            code = code.strip().upper()
            all_chips = get_cached_chips()
            matched_chip = None
            cand_norm = normalize_code_helper(code)
            
            for chip in all_chips:
                if cand_norm == normalize_code_helper(chip.code) or (chip.alias and cand_norm == normalize_code_helper(chip.alias)):
                    matched_chip = chip
                    break
                if chip.alternate_codes:
                    alts = [normalize_code_helper(c) for c in chip.alternate_codes.split(',') if c.strip()]
                    if cand_norm in alts:
                        matched_chip = chip
                        break
            
            if matched_chip:
                chip_data = {
                    'code': matched_chip.code,
                    'grade': matched_chip.grade,
                    'size': matched_chip.size,
                    'type': matched_chip.type,
                    'maker': matched_chip.maker,
                    'note': matched_chip.note,
                    'status': matched_chip.status,
                    'alias': matched_chip.alias,
                    'alternate_codes': matched_chip.alternate_codes,
                    'image_url': (settings.MEDIA_URL + matched_chip.image_path) if matched_chip.image_path else None
                }
                return JsonResponse({'exists': True, 'chip': chip_data})
            else:
                return JsonResponse({'exists': False})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 👤 USER MANAGEMENT ENDPOINTS
# ==================================================================
@csrf_exempt
def api_users(request):
    if request.method in ('GET', 'POST'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
    if request.method == 'GET':
        try:
            users = Technician.objects.all()
            data = [{'username': u.username, 'role': u.role} for u in users]
            return JsonResponse(data, safe=False)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            role = data.get('role', 'tech').strip()
            
            if not username or not password:
                return JsonResponse({'success': False, 'message': 'Username and password are required'}, status=400)
                
            if Technician.objects.filter(username__iexact=username).exists():
                return JsonResponse({'success': False, 'message': 'User already exists'}, status=400)
                
            Technician.objects.create(username=username, password=password, role=role)
            return JsonResponse({'success': True, 'message': f'User {username} created'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_delete_user(request, username):
    if request.method in ('POST', 'DELETE'):
        if not check_admin_role_helper(request):
            return JsonResponse({'success': False, 'message': 'Admin access required.'}, status=403)
    if request.method in ('POST', 'DELETE'):
        try:
            user = Technician.objects.filter(username__iexact=username).first()
            if not user:
                return JsonResponse({'success': False, 'message': f'User {username} not found'}, status=404)
            user.delete()
            return JsonResponse({'success': True, 'message': f'User {username} successfully deleted'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


def normalize_code_helper(text):
    if not text:
        return ""
    s = text.upper()
    s = re.sub(r'[\r\n\s]+', '', s)
    return re.sub(r'[^A-Z0-9]', '', s)


# ==================================================================
# 🔐 ADMIN ROLE VALIDATION HELPER
# ==================================================================
def check_admin_role_helper(request):
    """Helper to check if request is from an admin user"""
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
        
    if role and role.strip().lower() == 'admin':
        return True
        
    if username:
        user = Technician.objects.filter(username__iexact=username).first()
        if user and user.role and user.role.strip().lower() == 'admin':
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
            image_file = request.FILES.get('image')
            if image_file is not None:
                data = request.POST
            else:
                try:
                    data = json.loads(request.body)
                except Exception:
                    data = request.POST
            
            raw_code = data.get('code')
            code = raw_code.strip().upper() if isinstance(raw_code, str) else ''
            
            raw_user = data.get('user')
            username = raw_user.strip() if isinstance(raw_user, str) else ''
            
            raw_size = data.get('size')
            size = raw_size.strip() if isinstance(raw_size, str) else ''
            
            raw_type = data.get('type')
            chip_type = raw_type.strip() if isinstance(raw_type, str) else ''
            
            raw_classification = data.get('classification')
            classification = raw_classification.strip().lower() if isinstance(raw_classification, str) else ''
            if not classification:
                raw_status = data.get('status')
                classification = raw_status.strip().lower() if isinstance(raw_status, str) else 'coded'
            
            if not code or not username:
                return JsonResponse({'success': False, 'message': 'Code and user are required'}, status=400)
            
            # Check if this request is already pending
            existing = ApprovalRequest.objects.filter(code=code, technician=username, status='pending').first()
            if existing:
                return JsonResponse({'success': True, 'message': 'Request is already pending admin review'})
            
            # Save uploaded image to scans/
            img_path = ''
            if image_file is not None:
                try:
                    import time
                    ext = os.path.splitext(image_file.name)[1].lower() or '.jpg'
                    safe_code = re.sub(r'[^A-Z0-9._-]', '_', code.upper())
                    filename = f"scan_{safe_code}_{int(time.time())}{ext}"
                    
                    rel_path = 'scans/' + filename
                    abs_path = os.path.join(settings.MEDIA_ROOT, rel_path.replace('/', os.sep))
                    os.makedirs(os.path.dirname(abs_path), exist_ok=True)
                    with open(abs_path, 'wb') as f:
                        for chunk in image_file.chunks():
                            f.write(chunk)
                    img_path = rel_path
                except Exception as img_err:
                    print("Error saving technician submitted photo:", img_err)
            else:
                # Fallback to the latest ScanHistory image path for this user and code to attach
                latest_scan = ScanHistory.objects.filter(code=code, user=username).first()
                if latest_scan and latest_scan.image:
                    img_path = latest_scan.image.name
            
            # Create ApprovalRequest
            req = ApprovalRequest.objects.create(
                code=code,
                technician=username,
                status='pending',
                image_path=img_path,
                size=size,
                type=chip_type,
                classification=classification
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
            } for n in notifs.order_by('-created_at')[:50]]
            
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
                'size': r.size,
                'type': r.type,
                'classification': r.classification,
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
                grade = data.get('grade', 'A1')
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
                        save_chip_image(chip, image_file=image_file)
                    except Exception as img_err:
                        print("Approval chip image save error:", img_err)
                elif req.image_path:
                    try:
                        src_abs = os.path.join(settings.MEDIA_ROOT, req.image_path.replace('/', os.sep))
                        if os.path.exists(src_abs):
                            save_chip_image(chip, image_path_src=src_abs)
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

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Technician, Chip, Price, ScanHistory
import json

# ==================================================================
# 📊 LAZY DATABASE PRE-SEEDER
# Checks if the database is empty on page loads and seeds default records
# ==================================================================
def seed_database_if_empty():
    # 1. Seed default credentials if Technician table is empty
    if not Technician.objects.exists():
        Technician.objects.create(username='admin', password='admin123', role='admin')
        Technician.objects.create(username='tech1', password='tech123', role='tech')

    # 2. Seed standard chip buying rates if Price table is empty
    if not Price.objects.exists():
        default_prices = {
            'A5': (850, 600),
            'A4': (650, 450),
            'A3': (450, 300),
            'A2': (300, 200),
            'A1': (120, 80)
        }
        for grade, (coded, noncode) in default_prices.items():
            Price.objects.create(grade=grade, price_coded=coded, price_noncode=noncode)

    # 3. Seed 28 built-in eMMC/UFS storage chips if Chip table is empty
    if not Chip.objects.exists():
        DEFAULT_CHIPS = [
            # Samsung eMMC Models
            { 'code': 'KMRX1000BM', 'grade': 'A3', 'size': '32GB', 'type': 'eMMC 5.1', 'maker': 'Samsung', 'note': 'Galaxy J7 Prime storage' },
            { 'code': 'KMR820001M-B611', 'grade': 'A2', 'size': '16GB', 'type': 'eMMC 5.1', 'maker': 'Samsung', 'note': 'Mid-range eMMC core' },
            { 'code': 'KMR21000BM-B809', 'grade': 'A3', 'size': '32GB', 'type': 'eMMC 5.1', 'maker': 'Samsung', 'note': 'Premium eMMC assembly' },
            { 'code': 'KMQE60013M-B318', 'grade': 'A2', 'size': '8GB', 'type': 'eMMC 5.0', 'maker': 'Samsung', 'note': 'Legacy entry-level' },
            { 'code': 'KMGX6001BM-B514', 'grade': 'A2', 'size': '16GB', 'type': 'eMMC 5.1', 'maker': 'Samsung', 'note': 'Galaxy A-series standard' },
            { 'code': 'KMDH6001DM-B422', 'grade': 'A1', 'size': '8GB', 'type': 'eMMC 4.5', 'maker': 'Samsung', 'note': 'Older generation' },
            { 'code': 'KMWX6001LM-B612', 'grade': 'A2', 'size': '32GB', 'type': 'eMMC 5.1', 'maker': 'Samsung', 'note': 'Standard mid-range eMMC' },
            { 'code': 'KMFX6001DM-B503', 'grade': 'A2', 'size': '16GB', 'type': 'eMMC 5.0', 'maker': 'Samsung', 'note': 'Budget tier eMMC' },

            # Samsung UFS Models
            { 'code': 'KM8V7001JM-B810', 'grade': 'A5', 'size': '128GB', 'type': 'UFS 3.1', 'maker': 'Samsung', 'note': 'Flagship storage chip' },
            { 'code': 'KM5V7001JM-B622', 'grade': 'A4', 'size': '64GB', 'type': 'UFS 2.1', 'maker': 'Samsung', 'note': 'High-end UFS module' },
            { 'code': 'KM3V7001JM-B514', 'grade': 'A4', 'size': '32GB', 'type': 'UFS 2.0', 'maker': 'Samsung', 'note': 'Standard UFS 2.0' },
            { 'code': 'KM2V7001JM-B403', 'grade': 'A4', 'size': '16GB', 'type': 'UFS 2.0', 'maker': 'Samsung', 'note': 'UFS older-gen module' },
            { 'code': 'KM8X7001AM-B900', 'grade': 'A5', 'size': '256GB', 'type': 'UFS 3.1', 'maker': 'Samsung', 'note': 'Ultra high-end storage' },

            # SK Hynix eMMC Models
            { 'code': 'H9TQ26ADFTBCUR', 'grade': 'A3', 'size': '16GB', 'type': 'eMMC 5.1', 'maker': 'SK Hynix', 'note': 'Xiaomi Redmi Note storage' },
            { 'code': 'H9TQ64ABJTMCUR', 'grade': 'A3', 'size': '32GB', 'type': 'eMMC 5.1', 'maker': 'SK Hynix', 'note': 'Oppo A3s primary storage' },
            { 'code': 'H9TQ65ABKMMDAR', 'grade': 'A2', 'size': '64GB', 'type': 'eMMC 5.1', 'maker': 'SK Hynix', 'note': 'Premium high capacity eMMC' },
            { 'code': 'H9HP52AECMMD', 'grade': 'A2', 'size': '16GB', 'type': 'eMMC 5.0', 'maker': 'SK Hynix', 'note': 'Older Hynix series' },
            { 'code': 'H9HP64AECMMD', 'grade': 'A3', 'size': '32GB', 'type': 'eMMC 5.1', 'maker': 'SK Hynix', 'note': 'Standard Hynix eMMC' },

            # SK Hynix UFS Models
            { 'code': 'H9HQ15AECMMDAR', 'grade': 'A5', 'size': '256GB', 'type': 'UFS 3.1', 'maker': 'SK Hynix', 'note': 'Flagship tier high speed' },
            { 'code': 'H9HQ52AECMMDAR', 'grade': 'A4', 'size': '128GB', 'type': 'UFS 2.2', 'maker': 'SK Hynix', 'note': 'Realme mid-range storage' },
            { 'code': 'H9HQ64AECMMDAR', 'grade': 'A4', 'size': '64GB', 'type': 'UFS 2.1', 'maker': 'SK Hynix', 'note': 'Hynix UFS standard' },

            # Toshiba/Kioxia eMMC and UFS
            { 'code': 'TYD10001AM', 'grade': 'A2', 'size': '8GB', 'type': 'eMMC 4.5', 'maker': 'Toshiba', 'note': 'Legacy tablet storage' },
            { 'code': 'TYD20002AM-B600', 'grade': 'A2', 'size': '16GB', 'type': 'eMMC 5.0', 'maker': 'Toshiba', 'note': 'Standard legacy Toshiba' },
            { 'code': 'TYE30003AM', 'grade': 'A1', 'size': '16GB', 'type': 'eMMC 4.5', 'maker': 'Kioxia', 'note': 'Older generation budget' },
            { 'code': 'TYE40004AM-B800', 'grade': 'A2', 'size': '32GB', 'type': 'eMMC 5.1', 'maker': 'Kioxia', 'note': 'Kioxia standard eMMC' },
            { 'code': 'TYE50005AM-UFS', 'grade': 'A4', 'size': '64GB', 'type': 'UFS 2.1', 'maker': 'Kioxia', 'note': 'Kioxia high speed UFS' }
        ]
        for chip in DEFAULT_CHIPS:
            Chip.objects.create(
                code=chip['code'],
                grade=chip['grade'],
                size=chip['size'],
                type=chip['type'],
                maker=chip['maker'],
                note=chip['note'],
                is_manual=False,
                status='coded'
            )


# ==================================================================
# 🌐 MAIN RENDER VIEW
# ==================================================================
def index(request):
    seed_database_if_empty()
    return render(request, 'scanner/index.html')


# ==================================================================
# 🔐 AUTH ENDPOINT
# ==================================================================
@csrf_exempt
def api_login(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            
            user = Technician.objects.filter(username__iexact=username, password=password).first()
            if user:
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
            'alias': getattr(x, 'alias', ''),
            'alternate_codes': getattr(x, 'alternate_codes', ''),
            'ocr_text': getattr(x, 'ocr_text', '')
        } for x in chips]
        return JsonResponse(data, safe=False)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
            grade = data.get('grade', 'A2')
            size = data.get('size', '16GB')
            chip_type = data.get('type', 'eMMC 5.1').strip()
            maker = data.get('maker', 'Samsung').strip()
            note = data.get('note', 'Custom entry').strip()
            status = data.get('status', 'coded').strip().lower()
            alias = data.get('alias', '').strip()
            alternate_codes = data.get('alternate_codes', '').strip()
            ocr_text = data.get('ocr_text', '').strip()

            if not code:
                return JsonResponse({'success': False, 'message': 'Code field is required'}, status=400)

            # ── Duplicate Detection (case-insensitive, authoritative server check) ──
            if Chip.objects.filter(code__iexact=code).exists():
                return JsonResponse({
                    'success': False,
                    'message': f'Duplicate chipset code detected: {code} already exists in the database.',
                    'duplicate': True
                }, status=400)

            Chip.objects.create(
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
            return JsonResponse({'success': True, 'message': f'Chip {code} successfully added'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 🔍 CHIP CODE CHECK ENDPOINT — real-time lookup
# ==================================================================
def api_check_chip(request, code):
    """
    GET /api/chips/<code>/check/
    Returns whether a chip exists in the database and its full record if found.
    Used by the frontend for real-time analysis, confidence scoring, and duplicate detection.
    """
    if request.method == 'GET':
        chip = Chip.objects.filter(code__iexact=code).first()
        if chip:
            p_obj = Price.objects.filter(grade=chip.grade).first()
            return JsonResponse({
                'exists': True,
                'chip': {
                    'code': chip.code,
                    'grade': chip.grade,
                    'size': chip.size,
                    'type': chip.type,
                    'maker': chip.maker,
                    'note': chip.note,
                    'is_manual': chip.is_manual,
                    'status': chip.status,
                    'alias': getattr(chip, 'alias', ''),
                    'alternate_codes': getattr(chip, 'alternate_codes', ''),
                    'ocr_text': getattr(chip, 'ocr_text', ''),
                    'price_coded': p_obj.price_coded if p_obj else 0,
                    'price_noncode': p_obj.price_noncode if p_obj else 0,
                }
            })
        return JsonResponse({'exists': False, 'chip': None})
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_delete_chip(request, code):
    if request.method == 'POST':
        try:
            chip = Chip.objects.filter(code__iexact=code, is_manual=True).first()
            if chip:
                chip.delete()
                return JsonResponse({'success': True, 'message': f'Chip {code} successfully deleted'})
            return JsonResponse({'success': False, 'message': 'Custom chip not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 💰 PRICING METRICS CONFIGURATOR
# ==================================================================
@csrf_exempt
def api_prices(request):
    if request.method == 'GET':
        prices = Price.objects.all()
        coded = {}
        noncode = {}
        for p in prices:
            coded[p.grade] = p.price_coded
            noncode[p.grade] = p.price_noncode
        return JsonResponse({
            'coded': coded,
            'noncode': noncode
        })
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            coded = data.get('coded', {})
            noncode = data.get('noncode', {})

            for grade in ['A5', 'A4', 'A3', 'A2', 'A1']:
                p_coded = coded.get(grade, 0)
                p_noncode = noncode.get(grade, 0)
                Price.objects.update_or_create(
                    grade=grade,
                    defaults={'price_coded': p_coded, 'price_noncode': p_noncode}
                )

            return JsonResponse({'success': True, 'message': 'Prices successfully synchronized'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 🕘 SCAN LOGGER & LOG HISTORY ENDPOINTS
# ==================================================================
@csrf_exempt
def api_history(request):
    if request.method == 'GET':
        username = request.GET.get('username', '').strip()
        role = request.GET.get('role', 'tech').strip()
        
        # If Admin, returns all logs. If Technician, returns only their own logs.
        if role == 'admin':
            logs = ScanHistory.objects.all()
        else:
            logs = ScanHistory.objects.filter(user=username)

        data = [{
            'code': x.code,
            'grade': x.grade,
            'size': x.size,
            'type': x.type,
            'maker': x.maker,
            'priceCoded': x.price_coded,
            'priceNonCode': x.price_noncode,
            'timestamp': x.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            'user': x.user,
            'status': x.status
        } for x in logs]
        return JsonResponse(data, safe=False)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip().upper()
            user = data.get('user', 'Anonymous').strip()
            
            # Allow posting the status directly, fallback to db chip status
            status = data.get('status', '').strip().lower()

            chip = Chip.objects.filter(code__iexact=code).first()
            if not chip:
                return JsonResponse({'success': False, 'message': 'Chip definition not found'}, status=404)

            if not status:
                status = chip.status

            p_obj = Price.objects.filter(grade=chip.grade).first()
            price_coded = p_obj.price_coded if p_obj else 0
            price_noncode = p_obj.price_noncode if p_obj else 0

            ScanHistory.objects.create(
                code=chip.code,
                grade=chip.grade,
                size=chip.size,
                type=chip.type,
                maker=chip.maker,
                price_coded=price_coded,
                price_noncode=price_noncode,
                user=user,
                status=status
            )
            return JsonResponse({'success': True, 'message': 'Scan successfully logged'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_clear_history(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            role = data.get('role', 'tech').strip()

            if role == 'admin':
                ScanHistory.objects.all().delete()
            else:
                ScanHistory.objects.filter(user=username).delete()

            return JsonResponse({'success': True, 'message': 'History successfully cleared'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# ⚙️ USER ADMINISTRATOR MANAGEMENT ENDPOINTS
# ==================================================================
@csrf_exempt
def api_users(request):
    if request.method == 'GET':
        users = Technician.objects.all()
        data = [{
            'username': x.username,
            'role': x.role,
            'password': x.password
        } for x in users]
        return JsonResponse(data, safe=False)
        
    elif request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username', '').strip()
            password = data.get('password', '').strip()
            role = data.get('role', 'tech').strip()

            if not username or not password:
                return JsonResponse({'success': False, 'message': 'All fields are required'}, status=400)

            if Technician.objects.filter(username__iexact=username).exists():
                return JsonResponse({'success': False, 'message': 'Username account already exists'}, status=400)

            Technician.objects.create(username=username, password=password, role=role)
            return JsonResponse({'success': True, 'message': f'Registered account {username}'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
            
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def api_delete_user(request, username):
    if request.method == 'POST':
        try:
            if username.lower() == 'admin':
                return JsonResponse({'success': False, 'message': 'Cannot delete default admin profile'}, status=403)
                
            user = Technician.objects.filter(username__iexact=username).first()
            if user:
                user.delete()
                return JsonResponse({'success': True, 'message': f'Deleted user {username}'})
            return JsonResponse({'success': False, 'message': 'User account not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)


# ==================================================================
# 🔐 ADMIN SYSTEM METRICS (With classification separation)
# ==================================================================
def api_stats(request):
    if request.method == 'GET':
        total_scans = ScanHistory.objects.count()
        tech_count = Technician.objects.filter(role='tech').count()
        
        # Split database stats by status
        total_chips = Chip.objects.count()
        total_coded = Chip.objects.filter(status='coded').count()
        total_noncode = Chip.objects.filter(status='noncode').count()
        
        manual_added = Chip.objects.filter(is_manual=True).count()

        return JsonResponse({
            'scans': total_scans,
            'techs': tech_count,
            'db_total': total_chips,
            'coded_total': total_coded,
            'noncode_total': total_noncode,
            'manual_total': manual_added
        })
    return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)

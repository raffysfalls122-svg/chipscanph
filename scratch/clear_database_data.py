import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

from scanner.models import Chip, ScanHistory, Price, NonCodePrice, Technician, ApprovalRequest, Notification
from scanner.views import seed_database_if_empty, clear_scan_caches

print("=================== CLEARING DATABASE DATA ===================")
try:
    print("Deleting all ScanHistory records...")
    ScanHistory.objects.all().delete()

    print("Deleting all Chip records...")
    Chip.objects.all().delete()

    print("Deleting all Price records...")
    Price.objects.all().delete()

    print("Deleting all NonCodePrice records...")
    NonCodePrice.objects.all().delete()

    print("Deleting all ApprovalRequest records...")
    ApprovalRequest.objects.all().delete()

    print("Deleting all Notification records...")
    Notification.objects.all().delete()

    print("Deleting uploaded physical media files...")
    import shutil
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for folder in ['images', 'scans', '.uploads']:
        dir_path = os.path.join(base_dir, folder)
        if os.path.exists(dir_path):
            print(f"Cleaning physical folder: {folder}")
            for filename in os.listdir(dir_path):
                file_path = os.path.join(dir_path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}: {e}")

    # Retain the technicians table so user logins are not logged out,
    # but seed_database_if_empty will check and heal default admin/tech1 accounts.

    print("Re-seeding standard default dataset...")
    seed_database_if_empty()
    clear_scan_caches()

    print("=================== DATABASE DATA RESET SUCCESSFULLY ===================")
except Exception as e:
    print(f"Error resetting database: {e}")
    sys.exit(1)

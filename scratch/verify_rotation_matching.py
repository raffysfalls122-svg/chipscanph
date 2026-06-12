import os
import sys
import django

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chipscan.settings')
django.setup()

from django.conf import settings
from PIL import Image
from scanner.models import Chip
from scanner.views import run_image_matching_task

def verify_rotations():
    print("=================== VERIFYING ROTATION-INVARIANT MATCHING ===================")
    
    # Find a chip that has a reference photo
    target_chip = None
    for chip in Chip.objects.all():
        if chip.image_path and os.path.exists(os.path.join(settings.MEDIA_ROOT, chip.image_path.replace('/', os.sep))):
            target_chip = chip
            break
            
    if not target_chip:
        print("No chip with reference image found. Seeding one for testing...")
        # Let's see if there is any image we can use or if we can generate one.
        # Generate a dummy test image
        img = Image.new('RGB', (200, 200), color=(73, 109, 137))
        from PIL import ImageDraw
        d = ImageDraw.Draw(img)
        d.text((10, 10), "TEST CHIP", fill=(255, 255, 0))
        
        # Save it to a temporary reference
        os.makedirs(os.path.join(settings.MEDIA_ROOT, 'images', 'chips'), exist_ok=True)
        temp_rel_path = 'images/chips/TEST_CHIP.jpg'
        temp_abs_path = os.path.join(settings.MEDIA_ROOT, temp_rel_path.replace('/', os.sep))
        img.save(temp_abs_path)
        
        # Compute its hash
        from scanner.views import compute_image_hash
        img_hash = compute_image_hash(img)
        
        target_chip = Chip.objects.create(
            code="TEST_ROTATION_CHIP",
            grade="A2",
            size="32GB",
            type="eMMC",
            status="coded",
            image_path=temp_rel_path,
            image_hash=img_hash,
            is_manual=True
        )
        print(f"Created temporary chip {target_chip.code} with hash {target_chip.image_hash}")

    image_path = os.path.join(settings.MEDIA_ROOT, target_chip.image_path.replace('/', os.sep))
    print(f"Using chip: {target_chip.code}")
    print(f"Image Path: {image_path}")
    print(f"Stored Hash: {target_chip.image_hash}")
    
    # Load image
    orig_img = Image.open(image_path)
    
    all_chips = list(Chip.objects.all())
    
    # Test all 4 rotations
    angles = [0, 90, 180, 270]
    success = True
    
    for angle in angles:
        print(f"\n--- Testing Rotation: {angle}° ---")
        rotated_img = orig_img if angle == 0 else orig_img.rotate(angle, expand=True)
        
        scan_hash, matched_chip, distance = run_image_matching_task(rotated_img, all_chips)
        
        print(f"Scan Hash: {scan_hash}")
        print(f"Matched Chip: {matched_chip.code if matched_chip else 'None'}")
        print(f"Hamming Distance: {distance}")
        
        if not matched_chip:
            print(f"ERROR: Rotation {angle}° failed to match!")
            success = False
        elif matched_chip.code != target_chip.code:
            print(f"ERROR: Rotation {angle}° matched wrong chip: {matched_chip.code}")
            success = False
        else:
            print(f"SUCCESS: Rotation {angle}° successfully matched {matched_chip.code} (dist={distance})")
            
    # Cleanup temporary chip if we created it
    if target_chip.code == "TEST_ROTATION_CHIP":
        target_chip.delete()
        if os.path.exists(temp_abs_path):
            os.remove(temp_abs_path)
        print("Cleaned up temporary testing data.")
        
    if success:
        print("\n=================== ROTATION TEST SUCCESSFUL! ===================")
        sys.exit(0)
    else:
        print("\n=================== ROTATION TEST FAILED! ===================")
        sys.exit(1)

if __name__ == '__main__':
    verify_rotations()

from django.db import models

class Technician(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)  # For repair shop simplicity, plain text is used
    role = models.CharField(max_length=10, choices=[('admin', 'Admin'), ('tech', 'Technician')], default='tech')

    def __str__(self):
        return f"{self.username} ({self.role})"

class Chip(models.Model):
    code = models.CharField(max_length=50, unique=True, db_index=True)
    grade = models.CharField(max_length=5)  # A5, A4, A3, A2, A1
    size = models.CharField(max_length=20)   # 8GB, 16GB, 32GB, 64GB, 128GB, 256GB, 512GB
    type = models.CharField(max_length=50)   # eMMC 5.1, UFS 3.1, UFS 2.1, etc.
    maker = models.CharField(max_length=50)  # Samsung, SK Hynix, Toshiba, Kioxia
    note = models.TextField(blank=True, default='')
    is_manual = models.BooleanField(default=False)
    status = models.CharField(max_length=15, choices=[('coded', 'Coded'), ('noncode', 'Non-Coded')], default='coded')
    alias = models.CharField(max_length=100, blank=True, default='')
    alternate_codes = models.CharField(max_length=200, blank=True, default='')
    ocr_text = models.TextField(blank=True, default='')
    reference_image = models.ImageField(upload_to='chips/', null=True, blank=True)
    image_hash = models.CharField(max_length=64, blank=True, default='')  # perceptual hash for image matching
    image_path = models.CharField(max_length=255, blank=True, default='', db_index=True)  # relative path under MEDIA, e.g. images/chips/CODE.jpg

    def __str__(self):
        return f"{self.code} - {self.size} ({self.grade}) [{self.status}]"

class Price(models.Model):
    grade = models.CharField(max_length=5)  # A5, A4, A3, A2, A1
    price_coded = models.IntegerField(default=0)
    price_noncode = models.IntegerField(default=0)
    role = models.CharField(max_length=10, choices=[('admin', 'Admin'), ('tech', 'Technician')], default='tech')

    class Meta:
        unique_together = ('grade', 'role')

    def __str__(self):
        return f"Price ({self.role}) {self.grade}: Coded={self.price_coded}, NonCode={self.price_noncode}"

class NonCodePrice(models.Model):
    size = models.CharField(max_length=20)  # 8GB, 16GB, 32GB, 64GB, 128GB, 256GB, 512GB
    price = models.IntegerField(default=0)
    role = models.CharField(max_length=10, choices=[('admin', 'Admin'), ('tech', 'Technician')], default='tech')

    class Meta:
        unique_together = ('size', 'role')

    def __str__(self):
        return f"NonCodePrice ({self.role}) {self.size}: {self.price}"


class ScanHistory(models.Model):
    code = models.CharField(max_length=50, db_index=True)
    grade = models.CharField(max_length=5)
    size = models.CharField(max_length=20)
    type = models.CharField(max_length=50)
    maker = models.CharField(max_length=50)
    price_coded = models.IntegerField()
    price_noncode = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=50)  # Stores username who scanned the chip
    status = models.CharField(max_length=15, default='coded')  # Coded or Non-Coded status during scan
    
    # New fields for Capstone Scanner requirements
    image = models.ImageField(upload_to='scans/', null=True, blank=True)
    ocr_text = models.TextField(blank=True, default='')
    matched_chip = models.ForeignKey(Chip, on_delete=models.SET_NULL, null=True, blank=True)
    scan_status = models.CharField(max_length=20, default='UNKNOWN')  # MATCHED or UNKNOWN

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.code} ({self.scan_status}) checked by {self.user} at {self.timestamp}"


class ApprovalRequest(models.Model):
    code = models.CharField(max_length=50)
    technician = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending')
    created_at = models.DateTimeField(auto_now_add=True)
    image_path = models.CharField(max_length=255, blank=True, default='')
    
    # Details filled by admin during approval
    size = models.CharField(max_length=20, blank=True, default='')
    type = models.CharField(max_length=50, blank=True, default='')
    classification = models.CharField(max_length=15, blank=True, default='')

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Request for {self.code} by {self.technician} ({self.status})"


class Notification(models.Model):
    user = models.CharField(max_length=50) # Target username, or 'admin'
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Notification for {self.user}: {self.message[:30]}"


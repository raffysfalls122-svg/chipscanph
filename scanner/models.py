from django.db import models

class Technician(models.Model):
    username = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=50)  # For repair shop simplicity, plain text is used
    role = models.CharField(max_length=10, choices=[('admin', 'Admin'), ('tech', 'Technician')], default='tech')

    def __str__(self):
        return f"{self.username} ({self.role})"

class Chip(models.Model):
    code = models.CharField(max_length=50, unique=True)
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

    def __str__(self):
        return f"{self.code} - {self.size} ({self.grade}) [{self.status}]"

class Price(models.Model):
    grade = models.CharField(max_length=5, unique=True)  # A5, A4, A3, A2, A1
    price_coded = models.IntegerField(default=0)
    price_noncode = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.grade}: Coded={self.price_coded}, NonCode={self.price_noncode}"

class ScanHistory(models.Model):
    code = models.CharField(max_length=50)
    grade = models.CharField(max_length=5)
    size = models.CharField(max_length=20)
    type = models.CharField(max_length=50)
    maker = models.CharField(max_length=50)
    price_coded = models.IntegerField()
    price_noncode = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    user = models.CharField(max_length=50)  # Stores username who scanned the chip
    status = models.CharField(max_length=15, default='coded')  # Coded or Non-Coded status during scan

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.code} ({self.status}) checked by {self.user} at {self.timestamp}"

from django.db import models

class Role(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name


class User(models.Model):
    fullname = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    mobile = models.CharField(max_length=15, unique=True, null=True, blank=True)
    
    password = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=False)   # ✅ added
    email_verified = models.BooleanField(default=False)

    
    role = models.ForeignKey(Role, on_delete=models.CASCADE)

    # Optional business logo for vendors
    business_logo = models.ImageField(upload_to='vendor_logos/', null=True, blank=True)

    

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.fullname


class Token(models.Model):
    """Simple token/credit balance for a user."""
    user = models.OneToOneField('User', on_delete=models.CASCADE, related_name='token')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.user.fullname} - {self.balance} tokens"

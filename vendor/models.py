from django.db import models

# Create your models here.
from django.db import models
from account.models import User

class category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name
class Store(models.Model):
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role__name__iexact': 'vendor'})
    
    store_name = models.CharField(max_length=200)
    description = models.TextField()
    
    category = models.ForeignKey(category, on_delete=models.CASCADE)
        
    address = models.TextField()
    city = models.CharField(max_length=100)
    
    price_start = models.DecimalField(max_digits=10, decimal_places=2)
    
    profile_image = models.ImageField(upload_to='store_images/', null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    status = models.BooleanField(default=True)  # active/inactive

    def __str__(self):
        return self.store_name

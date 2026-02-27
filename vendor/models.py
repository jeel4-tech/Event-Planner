from django.db import models
from django.conf import settings
from account.models import User
from user.models import Event, Payment, Review

class category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class Store(models.Model):
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'role__name__iexact': 'vendor'})
    
    store_name = models.CharField(max_length=200)
    description = models.TextField()
    phone = models.CharField(max_length=20, null=True, blank=True)
    
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

    @property
    def profile_image_url(self):
        """Return a valid URL for the profile image or None if the file is missing."""
        try:
            if self.profile_image and getattr(self.profile_image, 'name', None):
                if self.profile_image.storage.exists(self.profile_image.name):
                    return self.profile_image.url
        except Exception:
            pass
        return None


class StoreImage(models.Model):
    """Additional images for a store (allow multiple photos)"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='store_images/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.store.store_name} - image {self.id}"


class Service(models.Model):
    """Services offered by vendors"""
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='service_images/', null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.store.store_name} - {self.name}"


class Booking(models.Model):
    """Bookings/Orders connecting events with vendor stores"""
    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_CONFIRMED, 'Approved'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_CANCELLED, 'Rejected'),
    ]

    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name='bookings')
    service = models.ForeignKey(Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    customer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='customer_bookings')
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='vendor_bookings')
    
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    # Advance/deposit support
    advance_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    advance_required = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    advance_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    notes = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    booking_date = models.DateTimeField(null=True, blank=True)  # When the service will be provided

    def __str__(self):
        return f"{self.store.store_name} - {self.event.title}"

    def apply_advance(self, amount):
        """Apply an advance payment amount to the booking and update status if covered."""
        # Use simple arithmetic and leave transactional safety to the caller
        self.advance_paid = (self.advance_paid or 0) + amount
        # If advance_paid covers required amount, mark confirmed
        try:
            if self.advance_required and self.advance_paid >= self.advance_required:
                self.status = self.STATUS_CONFIRMED
        except Exception:
            pass
        self.save()


class VendorEarning(models.Model):
    """Track vendor earnings from bookings"""
    vendor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='earnings')
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name='earning')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)  # Platform commission %
    net_amount = models.DecimalField(max_digits=10, decimal_places=2)  # Amount after commission
    payment_status = models.CharField(max_length=20, choices=Payment.STATUS_CHOICES, default=Payment.STATUS_PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    @property
    def commission_amount(self):
        """Calculate commission amount"""
        return self.amount - self.net_amount

    def __str__(self):
        return f"{self.vendor.fullname} - ₹{self.net_amount}"


class AdvancePayment(models.Model):
    """Records advance/deposit transactions tied to a Booking."""
    STATUS_PENDING = 'pending'
    STATUS_SUCCEEDED = 'succeeded'
    STATUS_FAILED = 'failed'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_SUCCEEDED, 'Succeeded'),
        (STATUS_FAILED, 'Failed'),
    ]

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name='advance_payments')
    # Use the project's account.User model (string reference avoids circular import)
    user = models.ForeignKey('account.User', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=10, default='INR')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    gateway = models.CharField(max_length=100, blank=True, null=True)
    gateway_id = models.CharField(max_length=255, blank=True, null=True)
    gateway_response = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Advance #{self.id} - {self.booking} - {self.amount} {self.currency} - {self.status}"


class Chat(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    store = models.ForeignKey(Store, blank=True, null=True, on_delete=models.CASCADE, related_name='chats')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='user_chats')
    vendor = models.ForeignKey(User, limit_choices_to={'role__name__iexact': 'vendor'}, on_delete=models.CASCADE, related_name='vendor_chats')

    class Meta:
        unique_together = (('user', 'vendor'),)

    def __str__(self):
        return f"Chat between {self.user.fullname} and {self.vendor.fullname}"


class ExtraCharge(models.Model):
    """Additional charge or add-on a vendor can attach to a booking."""
    booking = models.ForeignKey('Booking', on_delete=models.CASCADE, related_name='extras')
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.title} — ₹{self.amount}"


class ChatMessage(models.Model):
    message = models.TextField()
    image = models.ImageField(upload_to='chat_images/', null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    chat = models.ForeignKey(Chat, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Message from {self.sender.fullname} at {self.created_at}"
    
class GalleryImage(models.Model):
    """Images uploaded by vendors for events they worked on"""
    event = models.ForeignKey('user.Event', on_delete=models.CASCADE, related_name='gallery_images')
    image = models.ImageField(upload_to='gallery/')
    description = models.TextField(blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"Gallery Image {self.id}"
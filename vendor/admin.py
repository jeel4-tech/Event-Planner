from django.contrib import admin
from .models import Store, Service, StoreImage, Booking, VendorEarning, AdvancePayment, Chat, ChatMessage, ExtraCharge


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
	list_display = ('id', 'store', 'event', 'customer', 'vendor', 'amount', 'advance_required', 'advance_paid', 'status', 'booking_date')
	list_filter = ('status', 'booking_date')
	search_fields = ('store__store_name', 'event__title', 'customer__fullname', 'vendor__fullname')


@admin.register(AdvancePayment)
class AdvancePaymentAdmin(admin.ModelAdmin):
	list_display = ('id', 'booking', 'user', 'amount', 'currency', 'status', 'gateway', 'created_at')
	list_filter = ('status', 'gateway')


@admin.register(VendorEarning)
class VendorEarningAdmin(admin.ModelAdmin):
	list_display = ('vendor', 'booking', 'net_amount', 'payment_status', 'paid_at')


admin.site.register(Store)
admin.site.register(Service)
admin.site.register(StoreImage)
admin.site.register(Chat)
admin.site.register(ChatMessage)
admin.site.register(ExtraCharge)

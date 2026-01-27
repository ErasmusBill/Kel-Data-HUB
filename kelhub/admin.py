from django.contrib import admin
from .models import Network, DataBundle, Order, TransactionLog


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ['name', 'key', 'is_active', 'created_at']
    list_filter = ['is_active']
    search_fields = ['name', 'key']


@admin.register(DataBundle)
class DataBundleAdmin(admin.ModelAdmin):
    list_display = ['network', 'capacity', 'price', 'is_active', 'last_updated']
    list_filter = ['network', 'is_active']
    search_fields = ['capacity', 'plan_code']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'recipient_phone', 'network', 'bundle', 'amount', 'status', 'created_at']
    list_filter = ['status', 'network', 'created_at']
    search_fields = ['id', 'recipient_phone', 'api_order_id']
    readonly_fields = ['id', 'created_at', 'updated_at']


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ['order', 'status_code', 'created_at']
    list_filter = ['status_code', 'created_at']
    readonly_fields = ['created_at']
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Network,
    DataBundle,
    Wallet,
    WalletTransaction,
    Order,
    TransactionLog,
    DatamartTransaction,
)




@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'key')
    ordering = ('name',)


@admin.register(DataBundle)
class DataBundleAdmin(admin.ModelAdmin):
    list_display = ('network', 'capacity', 'price_display', 'plan_code', 'is_active', 'last_synced')
    list_filter = ('network', 'is_active')
    search_fields = ('capacity', 'plan_code')
    ordering = ('network__name', 'price')

    def price_display(self, obj):
        return format_html('GH₵{}', obj.price)
    price_display.short_description = 'Price'  # type: ignore



@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_display', 'total_deposited_display', 'total_spent_display', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = (
        'balance',
        'total_deposited',
        'total_spent',
        'total_refunded',
        'created_at',
        'updated_at',
    )

    def balance_display(self, obj):
        return format_html('<strong style="color: green;">GH₵{}</strong>', obj.balance)
    balance_display.short_description = 'Balance'  # type: ignore

    def total_deposited_display(self, obj):
        return format_html('GH₵{}', obj.total_deposited)
    total_deposited_display.short_description = 'Total Deposited'  # type: ignore

    def total_spent_display(self, obj):
        return format_html('GH₵{}', obj.total_spent)
    total_spent_display.short_description = 'Total Spent'  # type: ignore

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'wallet_user',
        'transaction_type',
        'amount_display',
        'status',
        'balance_before',
        'balance_after',
        'created_at',
    )
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('wallet__user__username', 'payment_reference', 'description')
    readonly_fields = (
        'id',
        'wallet',
        'order',
        'transaction_type',
        'amount',
        'status',
        'payment_reference',
        'payment_method',
        'description',
        'balance_before',
        'balance_after',
        'metadata',
        'created_at',
        'updated_at',
    )
    ordering = ('-created_at',)

    def wallet_user(self, obj):
        return obj.wallet.user.username
    wallet_user.short_description = 'User'  # type: ignore

    def amount_display(self, obj):
        color = 'green' if obj.transaction_type in ['deposit', 'refund'] else 'red'
        sign = '+' if obj.transaction_type in ['deposit', 'refund'] else '-'
        return format_html('<strong style="color:{};">{} GH₵{}</strong>', color, sign, obj.amount)
    amount_display.short_description = 'Amount'  # type: ignore

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False



@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'short_id',
        'user',
        'network',
        'bundle_capacity',
        'phone_number',
        'amount_display',
        'payment_method',
        'status_display',
        'created_at',
        'status'
    )
    list_filter = ('status', 'payment_method', 'network', 'created_at')
    search_fields = ('id', 'user__username', 'phone_number', 'purchase_id', 'transaction_reference')
    readonly_fields = (
        'id',
        'paid_from_wallet',
        'wallet_balance_before',
        'wallet_balance_after',
        'purchase_id',
        'transaction_reference',
        'remaining_balance',
        'api_response',
        'geonetechResponse',
        'created_at',
        'updated_at',
    )
    ordering = ('-created_at',)

    fieldsets = (
        ('Order Info', {
            'fields': ('id', 'user', 'network', 'bundle', 'phone_number', 'amount')
        }),
        ('Payment', {
            'fields': ('payment_method', 'gateway', 'paid_from_wallet')
        }),
        ('Wallet Balances', {
            'fields': ('wallet_balance_before', 'wallet_balance_after')
        }),
        ('API Response', {
            'fields': ('purchase_id', 'transaction_reference', 'remaining_balance', 'api_response', 'geonetechResponse')
        }),
        ('Status', {
            'fields': ('status', 'failure_reason', 'refunded_at', 'refund_amount')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def short_id(self, obj):
        return str(obj.id)[:8]
    short_id.short_description = 'Order ID'  # type: ignore

    def bundle_capacity(self, obj):
        return obj.bundle.capacity
    bundle_capacity.short_description = 'Bundle'  # type: ignore

    def amount_display(self, obj):
        return format_html('GH₵{}', obj.amount)
    amount_display.short_description = 'Amount'  # type: ignore

    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'successful': 'green',
            'failed': 'red',
            'refunded': 'purple',
        }
        return format_html(
            '<strong style="color:{};">{}</strong>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status'  # type: ignore





@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'endpoint', 'status_code', 'created_at')
    list_filter = ('status_code', 'created_at')
    search_fields = ('order__id', 'endpoint')
    readonly_fields = (
        'order',
        'endpoint',
        'request_method',
        'request_payload',
        'request_headers',
        'response_payload',
        'status_code',
        'response_time',
        'error_message',
        'created_at',
    )
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False




@admin.register(DatamartTransaction)
class DatamartTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'reference',
        'transaction_type',
        'amount_display',
        'status',
        'gateway',
        'api_created_at',
    )
    list_filter = ('transaction_type', 'status', 'gateway')
    search_fields = ('reference', 'transaction_id', 'user_id')
    readonly_fields = (
        'transaction_id',
        'user_id',
        'transaction_type',
        'amount',
        'status',
        'reference',
        'gateway',
        'order',
        'api_created_at',
        'api_updated_at',
        'synced_at',
    )
    ordering = ('-api_created_at',)

    def amount_display(self, obj):
        return format_html('GH₵{}', obj.amount)
    amount_display.short_description = 'Amount'  # type: ignore

    def has_add_permission(self, request):
        return False

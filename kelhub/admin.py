from django.contrib import admin
from django.utils.html import format_html
from .models import Network, DataBundle, Wallet, WalletTransaction, Order, TransactionLog


@admin.register(Network)
class NetworkAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'key')


@admin.register(DataBundle)
class DataBundleAdmin(admin.ModelAdmin):
    list_display = ('network', 'capacity', 'price', 'plan_code', 'is_active', 'last_updated')
    list_filter = ('network', 'is_active')
    search_fields = ('capacity', 'plan_code')
    ordering = ('network', 'price')


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_display', 'total_deposited_display', 'total_spent_display', 'created_at')
    search_fields = ('user__username', 'user__email')
    readonly_fields = ('balance', 'total_deposited', 'total_spent', 'created_at', 'updated_at')
    
    def balance_display(self, obj):
        return format_html(
            '<strong style="color: green;">GH₵{}</strong>',
            obj.balance
        )
    balance_display.short_description = 'Balance' # type: ignore
    
    def total_deposited_display(self, obj):
        return format_html('GH₵{}', obj.total_deposited)
    total_deposited_display.short_description = 'Total Deposited' # type: ignore
    
    def total_spent_display(self, obj):
        return format_html('GH₵{}', obj.total_spent)
    total_spent_display.short_description = 'Total Spent' # type: ignore
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of wallets
        return False


@admin.register(WalletTransaction)
class WalletTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'wallet_user', 'transaction_type', 'amount_display', 
        'status', 'balance_before', 'balance_after', 'created_at'
    )
    list_filter = ('transaction_type', 'status', 'created_at')
    search_fields = ('wallet__user__username', 'payment_reference', 'description')
    readonly_fields = (
        'id', 'wallet', 'transaction_type', 'amount', 'order', 
        'payment_reference', 'payment_method', 'status', 'description',
        'balance_before', 'balance_after', 'created_at', 'updated_at'
    )
    ordering = ('-created_at',)
    
    def wallet_user(self, obj):
        return obj.wallet.user.username
    wallet_user.short_description = 'User' # type: ignore
    
    def amount_display(self, obj):
        color = 'green' if obj.transaction_type == 'deposit' else 'red'
        symbol = '+' if obj.transaction_type in ['deposit', 'refund'] else '-'
        return format_html(
            '<strong style="color: {};">{} GH₵{}</strong>',
            color, symbol, obj.amount
        )
    amount_display.short_description = 'Amount' # type: ignore
    
    def has_add_permission(self, request):
        # Prevent manual creation
        return False
    
    def has_delete_permission(self, request, obj=None):
        # Prevent deletion of transaction records
        return False


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'network', 'bundle_capacity', 'recipient_phone',
        'amount_display', 'payment_method', 'status_display', 'created_at'
    )
    list_filter = ('status', 'payment_method', 'network', 'created_at')
    search_fields = ('id', 'user__username', 'recipient_phone', 'api_order_id', 'api_reference')
    readonly_fields = (
        'id', 'created_at', 'updated_at', 'api_order_id', 
        'api_reference', 'paid_from_wallet'
    )
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Order Information', {
            'fields': ('id', 'user', 'network', 'bundle', 'recipient_phone', 'amount')
        }),
        ('Payment Information', {
            'fields': ('payment_method', 'paid_from_wallet')
        }),
        ('Status & API', {
            'fields': ('status', 'failure_reason', 'api_order_id', 'api_reference')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def bundle_capacity(self, obj):
        return obj.bundle.capacity
    bundle_capacity.short_description = 'Bundle' # type: ignore
    
    def amount_display(self, obj):
        return format_html('GH₵{}', obj.amount)
    amount_display.short_description = 'Amount' # type: ignore
    
    def status_display(self, obj):
        colors = {
            'pending': 'orange',
            'processing': 'blue',
            'successful': 'green',
            'failed': 'red',
            'refunded': 'purple',
        }
        return format_html(
            '<strong style="color: {};">{}</strong>',
            colors.get(obj.status, 'black'),
            obj.get_status_display()
        )
    status_display.short_description = 'Status' # type: ignore


@admin.register(TransactionLog)
class TransactionLogAdmin(admin.ModelAdmin):
    list_display = ('order', 'status_code', 'created_at')
    list_filter = ('status_code', 'created_at')
    search_fields = ('order__id',)
    readonly_fields = ('order', 'request_payload', 'response_payload', 'status_code', 'created_at')
    ordering = ('-created_at',)
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
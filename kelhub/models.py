from decimal import Decimal
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F
from django.utils import timezone

from users.models import CustomUser




class Network(models.Model):
    NETWORK_CHOICES = (
        ('YELLO', 'MTN (Yello)'),
        ('TELECEL', 'Telecel (Vodafone)'),
        ('AT_PREMIUM', 'AirtelTigo Premium'),
    )

    key = models.CharField(max_length=20, unique=True, choices=NETWORK_CHOICES, help_text="DataMart API network code")
    name = models.CharField(max_length=50, help_text="Display name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        verbose_name = "Network"
        verbose_name_plural = "Networks"

    def __str__(self):
        return f"{self.name} ({self.key})"


class DataBundle(models.Model):
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="bundles")
    capacity = models.CharField(max_length=20, help_text="Data capacity value (e.g. 5 for 5GB)")
    mb = models.CharField(max_length=20, help_text="MB equivalent (e.g. 5000)")
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))], help_text="Bundle price in GH₵")
    plan_code = models.CharField(max_length=50, help_text="Internal plan identifier")
    is_active = models.BooleanField(default=True)
    last_synced = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("network", "capacity")
        ordering = ['network__name', 'price']
        verbose_name = "Data Bundle"
        verbose_name_plural = "Data Bundles"
        indexes = [
            models.Index(fields=['network', 'is_active']),
            models.Index(fields=['price']),
        ]

    def __str__(self):
        return f"{self.network.name} - {self.capacity}GB (GH₵{self.price})"

    @property
    def display_capacity(self):
        return f"{self.capacity}GB"



class Wallet(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'), validators=[MinValueValidator(Decimal('0.00'))])
    total_deposited = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total_refunded = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Wallet"
        verbose_name_plural = "Wallets"

    def __str__(self):
        return f"{self.user.username}'s Wallet - GH₵{self.balance}"

    def can_purchase(self, amount):
        return self.balance >= amount

    def deposit(self, amount):
        if amount <= 0:
            return False, "Deposit amount must be greater than zero"
        self.balance = F('balance') + amount
        self.total_deposited = F('total_deposited') + amount
        self.save(update_fields=['balance', 'total_deposited', 'updated_at'])
        self.refresh_from_db()
        return True, f"Successfully deposited GH₵{amount}"

    def deduct(self, amount):
        if amount <= 0:
            return False, "Amount must be greater than zero"
        if not self.can_purchase(amount):
            return False, "Insufficient balance"
        self.balance = F('balance') - amount
        self.total_spent = F('total_spent') + amount
        self.save(update_fields=['balance', 'total_spent', 'updated_at'])
        self.refresh_from_db()
        return True, f"Successfully deducted GH₵{amount}"

    def refund(self, amount):
        if amount <= 0:
            return False, "Refund amount must be greater than zero"
        self.balance = F('balance') + amount
        self.total_refunded = F('total_refunded') + amount
        self.save(update_fields=['balance', 'total_refunded', 'updated_at'])
        self.refresh_from_db()
        return True, f"Successfully refunded GH₵{amount}"


class WalletTransaction(models.Model):
    TRANSACTION_TYPES = (('deposit', 'Deposit'), ('purchase', 'Purchase'), ('refund', 'Refund'))
    STATUS_CHOICES = (('pending', 'Pending'), ('completed', 'Completed'), ('failed', 'Failed'))

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    order = models.ForeignKey('Order', on_delete=models.SET_NULL, null=True, blank=True, related_name='wallet_transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True)
    description = models.TextField(blank=True)
    metadata = models.JSONField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Wallet Transaction"
        verbose_name_plural = "Wallet Transactions"

    def __str__(self):
        return f"{self.get_transaction_type_display()} - GH₵{self.amount}"




class Order(models.Model):
    STATUS_CHOICES = (('pending', 'Pending'), ('processing', 'Processing'), ('successful', 'Successful'), ('failed', 'Failed'), ('refunded', 'Refunded'))
    PAYMENT_METHODS = (('wallet', 'Wallet'), ('mobile_money', 'Mobile Money'))
    GATEWAY_CHOICES = (('wallet', 'Wallet'),)

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='orders')
    network = models.ForeignKey(Network, on_delete=models.PROTECT)
    bundle = models.ForeignKey(DataBundle, on_delete=models.PROTECT)
    phone_number = models.CharField(max_length=15, db_column='recipient_phone')
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(Decimal('0.01'))])
    gateway = models.CharField(max_length=20, choices=GATEWAY_CHOICES, default='wallet')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='wallet')
    paid_from_wallet = models.BooleanField(default=False)
    wallet_balance_before = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    wallet_balance_after = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    purchase_id = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    transaction_reference = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    api_response = models.JSONField(blank=True, null=True)
    geonetechResponse = models.JSONField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', db_index=True)
    failure_reason = models.TextField(blank=True, null=True)
    refunded_at = models.DateTimeField(blank=True, null=True)
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    def __str__(self):
        return f"Order {str(self.id)[:8]} - {self.phone_number} - {self.get_status_display()}"

class TransactionLog(models.Model):
    user = models.ForeignKey(CustomUser,on_delete=models.CASCADE, related_name="transaction_log")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="api_logs")
    endpoint = models.CharField(max_length=200)
    request_method = models.CharField(max_length=10, default='POST')
    request_payload = models.JSONField()
    request_headers = models.JSONField(blank=True, null=True)
    response_payload = models.JSONField()
    status_code = models.PositiveIntegerField()
    response_time = models.FloatField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Transaction Log"
        verbose_name_plural = "Transaction Logs"

    def __str__(self):
        return f"Log {str(self.order.id)[:8]} - {self.endpoint}"




class DatamartTransaction(models.Model):
    TRANSACTION_TYPES = (('purchase', 'Purchase'), ('deposit', 'Deposit'), ('refund', 'Refund'))
    STATUS_CHOICES = (('completed', 'Completed'), ('pending', 'Pending'), ('failed', 'Failed'))

    transaction_id = models.CharField(max_length=100, unique=True)
    user_id = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES, db_column='type')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    reference = models.CharField(max_length=100)
    gateway = models.CharField(max_length=50)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True, related_name='datamart_transactions')
    api_created_at = models.DateTimeField()
    api_updated_at = models.DateTimeField()
    synced_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-api_created_at']
        verbose_name = "DataMart Transaction"
        verbose_name_plural = "DataMart Transactions"

    def __str__(self):
        return f"{self.reference} - {self.get_transaction_type_display()} - GH₵{self.amount}" # type: ignore
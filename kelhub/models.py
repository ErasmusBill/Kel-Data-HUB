from django.conf import settings
from django.db import models
from django.core.validators import MinValueValidator
from django.db.models import F
import uuid


class Network(models.Model):
    """
    Telecom networks (MTN/YELLO, AirtelTigo/AT_PREMIUM, TELECEL)
    """
    key = models.CharField(max_length=20, unique=True, help_text="API network code")
    name = models.CharField(max_length=50, help_text="Display name")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class DataBundle(models.Model):
    """
    Data plans offered by a network
    """
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="bundles")
    plan_code = models.CharField(max_length=50)
    capacity = models.CharField(max_length=20, help_text="e.g., 5GB")
    mb = models.CharField(max_length=20, help_text="MB equivalent", default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("network", "plan_code")
        ordering = ['price']

    def __str__(self):
        return f"{self.network.name} - {self.capacity} (GH₵{self.price})"


class Wallet(models.Model):
    """
    User wallet for data purchases - deposits only, no withdrawals
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='wallet'
    )
    balance = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)]
    )
    total_deposited = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total amount ever deposited (cannot be withdrawn)"
    )
    total_spent = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        help_text="Total amount spent on purchases"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.username}'s Wallet - GH₵{self.balance}"

    def deposit(self, amount):
        """
        Deposit money into wallet
        Returns: (success, message)
        """
        if amount <= 0:
            return False, "Deposit amount must be greater than zero"
        
        self.balance = F('balance') + amount
        self.total_deposited = F('total_deposited') + amount
        self.save(update_fields=['balance', 'total_deposited', 'updated_at'])
        self.refresh_from_db()
        return True, f"Successfully deposited GH₵{amount}"

    def can_purchase(self, amount):
        """Check if wallet has sufficient balance"""
        return self.balance >= amount

    def deduct(self, amount, order):
        """
        Deduct amount for purchase
        Returns: (success, message)
        """
        if amount <= 0:
            return False, "Amount must be greater than zero"
        
        if not self.can_purchase(amount):
            return False, "Insufficient wallet balance"
        
        self.balance = F('balance') - amount
        self.total_spent = F('total_spent') + amount
        self.save(update_fields=['balance', 'total_spent', 'updated_at'])
        self.refresh_from_db()
        return True, f"Successfully deducted GH₵{amount}"


class WalletTransaction(models.Model):
    """
    Records all wallet transactions (deposits and purchases)
    """
    TRANSACTION_TYPES = (
        ('deposit', 'Deposit'),
        ('purchase', 'Purchase'),
        ('refund', 'Refund'),  # Only in case of failed orders
    )

    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # For purchase transactions
    order = models.ForeignKey(
        'Order',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='wallet_transactions'
    )
    
    # Payment reference (for deposits)
    payment_reference = models.CharField(max_length=100, blank=True, null=True)
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="e.g., Mobile Money, Card, Bank Transfer"
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    description = models.TextField(blank=True)
    
    # Balance after transaction
    balance_before = models.DecimalField(max_digits=10, decimal_places=2)
    balance_after = models.DecimalField(max_digits=10, decimal_places=2)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['wallet', '-created_at']),
            models.Index(fields=['transaction_type', '-created_at']),
        ]

    def __str__(self):
        return f"{self.transaction_type.title()} - GH₵{self.amount} - {self.status}"


class Order(models.Model):
    """
    Represents a data purchase order
    """
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("successful", "Successful"),
        ("failed", "Failed"),
        ("refunded", "Refunded"),
    )

    PAYMENT_METHODS = (
        ('wallet', 'Wallet'),
        ('mobile_money', 'Mobile Money'),
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders'
    )
    network = models.ForeignKey(Network, on_delete=models.PROTECT)
    bundle = models.ForeignKey(DataBundle, on_delete=models.PROTECT)
    recipient_phone = models.CharField(max_length=15)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Payment information
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHODS,
        default='wallet'
    )
    paid_from_wallet = models.BooleanField(default=False)
    
    # API response fields
    api_order_id = models.CharField(max_length=100, blank=True, null=True)
    api_reference = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    
    failure_reason = models.TextField(blank=True, null=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['-created_at']),
            models.Index(fields=['user', '-created_at']),
            models.Index(fields=['status', '-created_at']),
        ]

    def __str__(self):
        return f"Order {self.id} - {self.recipient_phone} - {self.status}"

    def process_payment(self):
        """
        Process payment from wallet
        Returns: (success, message)
        """
        if self.payment_method != 'wallet':
            return False, "This order is not set to use wallet payment"
        
        if not self.user:
            return False, "No user associated with this order"
        
        try:
            wallet = self.user.wallet
        except Wallet.DoesNotExist:
            return False, "User does not have a wallet"
        
        # Check if sufficient balance
        if not wallet.can_purchase(self.amount):
            return False, f"Insufficient balance. Required: GH₵{self.amount}, Available: GH₵{wallet.balance}"
        
        # Record balance before transaction
        balance_before = wallet.balance
        
        # Deduct from wallet
        success, message = wallet.deduct(self.amount, self)
        
        if success:
            self.paid_from_wallet = True
            self.save(update_fields=['paid_from_wallet', 'updated_at'])
            
            # Create wallet transaction record
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='purchase',
                amount=self.amount,
                order=self,
                status='completed',
                description=f"Purchase of {self.bundle.capacity} for {self.recipient_phone}",
                balance_before=balance_before,
                balance_after=wallet.balance
            )
            
        return success, message

    def refund_to_wallet(self):
        """
        Refund order amount back to wallet (only for failed orders)
        Returns: (success, message)
        """
        if self.status != 'failed':
            return False, "Can only refund failed orders"
        
        if not self.paid_from_wallet:
            return False, "This order was not paid from wallet"
        
        if self.status == 'refunded':
            return False, "This order has already been refunded"
        
        try:
            wallet = self.user.wallet
        except Wallet.DoesNotExist:
            return False, "User wallet not found"
        
        # Record balance before refund
        balance_before = wallet.balance
        
        # Add amount back to wallet
        success, message = wallet.deposit(self.amount)
        
        if success:
            self.status = 'refunded'
            self.save(update_fields=['status', 'updated_at'])
            
            # Create refund transaction record
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type='refund',
                amount=self.amount,
                order=self,
                status='completed',
                description=f"Refund for failed order - {self.bundle.capacity}",
                balance_before=balance_before,
                balance_after=wallet.balance
            )
            
        return success, message


class TransactionLog(models.Model):
    """
    Stores raw API requests/responses for debugging
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="logs")
    request_payload = models.JSONField()
    response_payload = models.JSONField()
    status_code = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Log for Order {self.order.id} - Status {self.status_code}"
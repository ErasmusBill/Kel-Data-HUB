from django.conf import settings
from django.db import models
import uuid
from django.utils import timezone

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
    mb = models.CharField(max_length=20, help_text="MB equivalent")
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("network", "plan_code")
        ordering = ['price']

    def __str__(self):
        return f"{self.network.name} - {self.capacity} (GH₵{self.price})"


class Order(models.Model):
    """
    Represents a data purchase order
    """
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("successful", "Successful"),
        ("failed", "Failed"),
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
    
    # API response fields
    api_order_id = models.CharField(max_length=100, blank=True, null=True)
    api_reference = models.CharField(max_length=100, blank=True, null=True)
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Order {self.id} - {self.recipient_phone} - {self.status}"


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
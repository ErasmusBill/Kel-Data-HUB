from django.conf import settings
from django.db import models
import uuid


class Network(models.Model):
    """
    Telecom networks like MTN, AIRTELTIGO, TELECEL
    """
    key = models.CharField(max_length=20, unique=True)  
    name = models.CharField(max_length=50)

    def __str__(self):
        return self.name


class DataBundle(models.Model):
    """
    Data plans offered by a network
    """
    network = models.ForeignKey(Network, on_delete=models.CASCADE, related_name="bundles")
    plan_code = models.CharField(max_length=50)  
    size = models.CharField(max_length=20)      
    price = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("network", "plan_code")

    def __str__(self):
        return f"{self.network.name} - {self.size}"


class Order(models.Model):
    """
    Represents a purchase request made to DataMartGH
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
        blank=True
    )

    network = models.ForeignKey(Network, on_delete=models.PROTECT)
    bundle = models.ForeignKey(DataBundle, on_delete=models.PROTECT)

    recipient_phone = models.CharField(max_length=15)

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    # External references from DataMartGH
    api_order_id = models.CharField(max_length=100, blank=True, null=True)
    api_reference = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.recipient_phone} - {self.bundle} - {self.status}"


class TransactionLog(models.Model):
    """
    Stores raw API responses for debugging & auditing
    """
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="logs")
    request_payload = models.JSONField()
    response_payload = models.JSONField()
    status_code = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Log for Order {self.order.id}"

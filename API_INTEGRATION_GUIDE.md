# DataMart Ghana API Integration Guide

## Complete Model Rewrite - API Specification Compliance

---

## 📋 API Specification Summary

### Base URL
```
https://datamartbackened.onrender.com/api/developer
```

### Authentication
```
Header: X-API-Key: your_api_key_here
```

### Supported Networks
- **YELLO** - MTN Ghana
- **TELECEL** - Vodafone (Telecel)
- **AT_PREMIUM** - AirtelTigo

---

## 🔌 API Endpoints

### 1. Get Data Packages

**Endpoint:** `GET /api/developer/data-packages`

**Query Parameters:**
- `network` (optional): Filter by network (YELLO, TELECEL, AT_PREMIUM)

**Request (Single Network):**
```bash
curl -X GET "https://datamartbackened.onrender.com/api/developer/data-packages?network=TELECEL" \
  -H "X-API-Key: your_api_key_here"
```

**Response (Single Network):**
```json
{
  "status": "success",
  "data": [
    {
      "capacity": "5",
      "mb": "5000",
      "price": "23.00",
      "network": "TELECEL"
    },
    {
      "capacity": "10",
      "mb": "10000",
      "price": "35.50",
      "network": "TELECEL"
    }
  ]
}
```

**Request (All Networks):**
```bash
curl -X GET "https://datamartbackened.onrender.com/api/developer/data-packages" \
  -H "X-API-Key: your_api_key_here"
```

**Response (All Networks):**
```json
{
  "status": "success",
  "data": {
    "TELECEL": [
      {"capacity": "5", "mb": "5000", "price": "23.00", "network": "TELECEL"}
    ],
    "YELLO": [
      {"capacity": "5", "mb": "5000", "price": "25.00", "network": "YELLO"}
    ],
    "AT_PREMIUM": [
      {"capacity": "5", "mb": "5000", "price": "24.00", "network": "AT_PREMIUM"}
    ]
  }
}
```

---

### 2. Purchase Data Bundle

**Endpoint:** `POST /api/developer/purchase`

**Request Body:**
```json
{
  "phoneNumber": "0551234567",
  "network": "TELECEL",
  "capacity": "5",
  "gateway": "wallet"
}
```

**Important Notes:**
- `phoneNumber` is **camelCase** (not snake_case)
- `capacity` is just the number WITHOUT "GB" (e.g., "5" not "5GB")
- `gateway` should be "wallet" for wallet payments

**Success Response:**
```json
{
  "status": "success",
  "data": {
    "purchaseId": "60f1e5b3e6b39812345678",
    "transactionReference": "TRX-a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "network": "TELECEL",
    "capacity": "5",
    "mb": "5000",
    "price": 23.00,
    "remainingBalance": 177.00,
    "geonetechResponse": {
      "code": "000",
      "message": "Transaction successful"
    }
  }
}
```

**Error Response:**
```json
{
  "status": "error",
  "message": "Insufficient balance"
}
```

---

### 3. Get Transactions (Optional)

**Endpoint:** `GET /api/developer/transactions`

**Response:**
```json
{
  "status": "success",
  "data": {
    "transactions": [
      {
        "_id": "60f1e5b3e6b39812345678",
        "userId": "60f1e5b3e6b39812345679",
        "type": "purchase",
        "amount": 23.00,
        "status": "completed",
        "reference": "TRX-a1b2c3d4-...",
        "gateway": "wallet",
        "createdAt": "2023-01-01T12:00:00.000Z",
        "updatedAt": "2023-01-01T12:00:00.000Z"
      }
    ]
  }
}
```

---

## 📊 Model-to-API Mapping

### Network Model → API Networks

| Model Field | API Field | Example |
|------------|----------|---------|
| `key` | `network` | "TELECEL" |
| `name` | N/A | "Telecel Ghana" |

**Supported Network Keys:**
```python
NETWORK_CHOICES = (
    ('YELLO', 'MTN (Yello)'),
    ('TELECEL', 'Telecel (Vodafone)'),
    ('AT_PREMIUM', 'AirtelTigo Premium'),
)
```

---

### DataBundle Model → API Data Package

| Model Field | API Field | Example | Notes |
|------------|-----------|---------|-------|
| `capacity` | `capacity` | "5" | Store as string WITHOUT "GB" |
| `mb` | `mb` | "5000" | Megabytes as string |
| `price` | `price` | Decimal("23.00") | Convert from string to Decimal |
| `network` | `network` | Network FK | Link to Network model |

**API Response Mapping:**
```python
# API returns:
{
  "capacity": "5",
  "mb": "5000", 
  "price": "23.00",
  "network": "TELECEL"
}

# Store as:
DataBundle.objects.create(
    network=telecel_network,  # FK to Network with key="TELECEL"
    capacity="5",             # String, not "5GB"
    mb="5000",                # String from API
    price=Decimal("23.00"),   # Convert to Decimal
    plan_code="5GB"           # Generated for display
)
```

---

### Order Model → API Purchase Request/Response

**Request Mapping:**
| Model Field | API Field | Example |
|------------|-----------|---------|
| `phone_number` | `phoneNumber` | "0551234567" |
| `network.key` | `network` | "TELECEL" |
| `bundle.capacity` | `capacity` | "5" |
| `gateway` | `gateway` | "wallet" |

**Response Mapping:**
| Model Field | API Field | Example |
|------------|-----------|---------|
| `purchase_id` | `purchaseId` | "60f1e5..." |
| `transaction_reference` | `transactionReference` | "TRX-..." |
| `remaining_balance` | `remainingBalance` | Decimal("177.00") |
| `geonetechResponse` | `geonetechResponse` | JSON object |
| `api_response` | Full response | Complete JSON |

---

## 🔧 Key Implementation Changes

### 1. Phone Number Field

**OLD:**
```python
recipient_phone = models.CharField(max_length=15)
```

**NEW:**
```python
phone_number = models.CharField(
    max_length=15,
    db_column='recipient_phone'  # Keep DB compatibility
)

@property
def recipient_phone(self):
    """Backwards compatibility"""
    return self.phone_number
```

**Reason:** API uses `phoneNumber` (camelCase), but we keep DB column name for backwards compatibility.

---

### 2. Capacity Storage

**OLD:**
```python
capacity = models.CharField(max_length=20, help_text="e.g., 5GB")
# Stored as: "5GB"
```

**NEW:**
```python
capacity = models.CharField(
    max_length=20, 
    help_text="Data capacity value (e.g., '5' for 5GB)"
)
# Store as: "5"

@property
def display_capacity(self):
    return f"{self.capacity}GB"
```

**Reason:** API expects just the number ("5"), not "5GB".

---

### 3. API Response Fields

**NEW FIELDS:**
```python
# Purchase tracking
purchase_id = models.CharField(max_length=100, blank=True, null=True)
transaction_reference = models.CharField(max_length=100, blank=True, null=True)
remaining_balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)

# Response storage
api_response = models.JSONField(blank=True, null=True)
geonetechResponse = models.JSONField(blank=True, null=True)

# Wallet tracking
wallet_balance_before = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
wallet_balance_after = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
```

---

### 4. Transaction Logging

**NEW MODEL:**
```python
class TransactionLog(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="api_logs")
    endpoint = models.CharField(max_length=200)
    request_method = models.CharField(max_length=10, default='POST')
    request_payload = models.JSONField()
    request_headers = models.JSONField(blank=True, null=True)
    response_payload = models.JSONField()
    status_code = models.PositiveIntegerField()
    response_time = models.FloatField(blank=True, null=True)
    error_message = models.TextField(blank=True, null=True)
```

**Logs every API call for debugging.**

---

### 5. DataMart Transaction Model

**NEW MODEL:**
```python
class DatamartTransaction(models.Model):
    """Mirror of DataMart API transaction structure"""
    transaction_id = models.CharField(max_length=100, unique=True)
    user_id = models.CharField(max_length=100)
    transaction_type = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20)
    reference = models.CharField(max_length=100)
    gateway = models.CharField(max_length=50)
    order = models.ForeignKey(Order, on_delete=models.SET_NULL, null=True, blank=True)
    api_created_at = models.DateTimeField()
    api_updated_at = models.DateTimeField()
```

**Purpose:** Store transactions fetched from DataMart API for reconciliation.

---

## 🚀 Complete Purchase Flow

### Step-by-Step Process

```
1. USER INITIATES PURCHASE
   └─> Order created with status='pending'

2. VALIDATE PHONE NUMBER
   └─> Format: 0551234567 (10 digits)
   
3. PROCESS WALLET PAYMENT
   ├─> Check wallet balance
   ├─> Deduct amount
   ├─> Set paid_from_wallet=True
   ├─> Record wallet_balance_before/after
   └─> Create WalletTransaction (type='purchase')

4. CALL DATAMART API
   ├─> POST /api/developer/purchase
   ├─> Request Body:
   │   {
   │     "phoneNumber": "0551234567",
   │     "network": "TELECEL",
   │     "capacity": "5",
   │     "gateway": "wallet"
   │   }
   ├─> Set order.status='processing'
   └─> Create TransactionLog

5a. API SUCCESS
   ├─> Extract response data:
   │   - purchaseId
   │   - transactionReference
   │   - remainingBalance
   │   - geonetechResponse
   ├─> Save to order
   ├─> Set status='successful'
   └─> Done!

5b. API FAILURE
   ├─> Set status='failed'
   ├─> Save failure_reason
   ├─> Trigger REFUND
   │   ├─> Add amount back to wallet
   │   ├─> Create WalletTransaction (type='refund')
   │   └─> Set order.status='refunded'
   └─> Done (user money returned)
```

---

## 💻 Code Examples

### Example 1: Sync Data Bundles

```python
from myapp.models import Network
from myapp.utils import sync_all_bundles

# Sync all networks at once
results = sync_all_bundles()
print(results)
# Output: {'YELLO': 15, 'TELECEL': 12, 'AT_PREMIUM': 10}

# Or sync single network
from myapp.utils import sync_data_bundles

telecel = Network.objects.get(key='TELECEL')
count = sync_data_bundles('TELECEL', telecel)
print(f"Synced {count} bundles")
```

---

### Example 2: Create and Process Order

```python
from django.db import transaction
from myapp.models import Order, DataBundle

@transaction.atomic
def create_order(user, bundle_id, phone):
    """Complete order flow with rollback on failure"""
    
    # Get bundle
    bundle = DataBundle.objects.select_related('network').get(id=bundle_id)
    
    # Create order
    order = Order.objects.create(
        user=user,
        network=bundle.network,
        bundle=bundle,
        phone_number=phone,  # Note: phone_number not recipient_phone
        amount=bundle.price,
        payment_method='wallet',
        gateway='wallet'
    )
    
    # Process wallet payment
    success, msg = order.process_payment()
    if not success:
        raise Exception(msg)
    
    # Purchase via API
    success, msg, data = order.process_api_purchase()
    
    if not success:
        # Auto-refund happens in process_api_purchase
        raise Exception(msg)
    
    return order

# Usage
try:
    order = create_order(request.user, bundle_id=5, phone="0551234567")
    print(f"Success! Purchase ID: {order.purchase_id}")
except Exception as e:
    print(f"Failed: {e}")
```

---

### Example 3: Check Transaction Logs

```python
from myapp.models import Order, TransactionLog

# Get order
order = Order.objects.get(id='some-uuid')

# View all API calls for this order
logs = order.api_logs.all()

for log in logs:
    print(f"Endpoint: {log.endpoint}")
    print(f"Status: {log.status_code}")
    print(f"Response Time: {log.response_time}s")
    print(f"Request: {log.request_payload}")
    print(f"Response: {log.response_payload}")
    print("---")
```

---

### Example 4: Phone Number Validation

```python
from myapp.utils import validate_phone_number

# Test various formats
phones = [
    "+233551234567",  # International
    "0551234567",     # Local
    "551234567",      # Without prefix
    "233551234567",   # Country code without +
]

for phone in phones:
    validated = validate_phone_number(phone)
    print(f"{phone} → {validated}")

# Output:
# +233551234567 → 0551234567
# 0551234567 → 0551234567
# 551234567 → 0551234567
# 233551234567 → 0551234567
```

---

## 🔄 Migration from Old Model

### Field Renames

```python
# migrations/XXXX_rename_fields.py

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', 'previous_migration'),
    ]

    operations = [
        # Rename api_order_id → purchase_id
        migrations.RenameField(
            model_name='order',
            old_name='api_order_id',
            new_name='purchase_id',
        ),
        
        # Rename api_reference → transaction_reference
        migrations.RenameField(
            model_name='order',
            old_name='api_reference',
            new_name='transaction_reference',
        ),
        
        # Rename logs → api_logs
        migrations.AlterField(
            model_name='transactionlog',
            name='order',
            field=models.ForeignKey(
                on_delete=models.CASCADE,
                related_name='api_logs',
                to='myapp.Order'
            ),
        ),
    ]
```

### Data Migration for Capacity

```python
# migrations/XXXX_fix_capacity_format.py

from django.db import migrations

def remove_gb_suffix(apps, schema_editor):
    """Remove 'GB' suffix from capacity field"""
    DataBundle = apps.get_model('myapp', 'DataBundle')
    
    for bundle in DataBundle.objects.all():
        if bundle.capacity.endswith('GB'):
            bundle.capacity = bundle.capacity[:-2].strip()
            bundle.save()

def add_gb_suffix(apps, schema_editor):
    """Add 'GB' suffix back (reverse migration)"""
    DataBundle = apps.get_model('myapp', 'DataBundle')
    
    for bundle in DataBundle.objects.all():
        if not bundle.capacity.endswith('GB'):
            bundle.capacity = f"{bundle.capacity}GB"
            bundle.save()

class Migration(migrations.Migration):
    dependencies = [
        ('myapp', 'previous_migration'),
    ]

    operations = [
        migrations.RunPython(remove_gb_suffix, add_gb_suffix),
    ]
```

---

## 🧪 Testing

### Test API Connection

```python
from myapp.utils import verify_api_key

if verify_api_key():
    print("✅ API key is valid")
else:
    print("❌ API key is invalid")
```

### Test Data Sync

```python
from myapp.utils import get_data_plans

# Test single network
plans = get_data_plans('TELECEL')
print(f"Found {len(plans)} plans for TELECEL")

# Test all networks
all_plans = get_data_plans()
for network, plans in all_plans.items():
    print(f"{network}: {len(plans)} plans")
```

### Test Purchase (Dry Run)

```python
# Don't actually purchase - just test the flow
from myapp.models import Order

order = Order(
    user=user,
    network=network,
    bundle=bundle,
    phone_number="0551234567",
    amount=bundle.price,
    gateway='wallet'
)

# Test phone validation
from myapp.utils import validate_phone_number
validated = validate_phone_number(order.phone_number)
print(f"Phone validation: {validated}")

# Test payload construction
payload = {
    "phoneNumber": validated,
    "network": order.network.key,
    "capacity": order.bundle.capacity,
    "gateway": order.gateway
}
print(f"API Payload: {payload}")
```

---

## ⚠️ Important Differences from Previous Model

### 1. Field Names
- `recipient_phone` → `phone_number` (with DB compatibility)
- `api_order_id` → `purchase_id`
- `api_reference` → `transaction_reference`
- `logs` (related_name) → `api_logs`

### 2. Capacity Storage
- OLD: "5GB" (with suffix)
- NEW: "5" (without suffix, add via `display_capacity` property)

### 3. New Required Fields
- `gateway` - Payment gateway for API
- `remaining_balance` - Balance from API response
- `wallet_balance_before/after` - Wallet tracking
- `refunded_at`, `refund_amount` - Refund tracking

### 4. New Models
- `DatamartTransaction` - Mirror API transactions
- `APIConfiguration` - Centralized API settings

### 5. Enhanced Logging
- `TransactionLog` now includes:
  - `endpoint`
  - `request_method`
  - `request_headers`
  - `response_time`
  - `error_message`

---

## 📝 Checklist for Implementation

- [ ] Update models.py with new version
- [ ] Update utils.py with API-compliant functions
- [ ] Create and run migrations
- [ ] Add 'refund' to WalletTransaction.TRANSACTION_TYPES
- [ ] Update admin.py for new fields
- [ ] Set API_KEY and API_BASE_URL in environment
- [ ] Create networks (YELLO, TELECEL, AT_PREMIUM)
- [ ] Sync data bundles from API
- [ ] Test phone number validation
- [ ] Test complete purchase flow
- [ ] Monitor TransactionLog for errors
- [ ] Set up error alerts for failed purchases

---

**Last Updated:** January 2026  
**API Version:** DataMart Ghana v1  
**Django Compatibility:** 4.x+
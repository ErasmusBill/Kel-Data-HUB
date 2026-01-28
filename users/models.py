from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import validate_email 
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid
from django.utils.crypto import get_random_string


class BaseModel(models.Model):
    """Abstract base model with common fields"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        

class CustomUser(AbstractUser, BaseModel):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('admin', 'Admin'),
    )
    """Custom user model extending AbstractUser"""
    full_name = models.CharField(max_length=30)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='customer')
    
    def validate_password(self, password):
        """Validate password strength"""
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long')
        return True
        
    def validate_user_email(self, email):
        """Validate email format"""
        try:
            validate_email(email)
            return True
        except ValidationError:
            raise ValidationError('Invalid email format')

    def __str__(self):
        return self.username


class Profile(BaseModel):
    """User profile model"""
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)

    def __str__(self):
        return f"Profile of {self.user.username}"


class ResetPasswordToken(BaseModel):
    """Model to store password reset tokens"""
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    expiry = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    def is_valid(self):
        """Check if token is valid"""
        if self.is_used:
            return False, 'Token has already been used'
        
        if timezone.now() > self.expiry:
            return False, 'Token has expired'
        
        return True, 'Token is valid'
    
    def generate_token(self):
        """Generate a unique token"""
        return get_random_string(length=50)
    
    def save(self, *args, **kwargs):
        """Set expiry to 1 hour from creation if not set"""
        if not self.expiry:
            self.expiry = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)
    
    
        
    def __str__(self):
        return f"Reset token for {self.user.username}"
    
    
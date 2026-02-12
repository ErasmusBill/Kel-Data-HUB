from django.shortcuts import render, redirect,get_object_or_404,resolve_url
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.urls import reverse
from kelhub.models import Network,DataBundle
from kelhub.models import Wallet
from .models import CustomUser, Profile, ResetPasswordToken
from .utils import send_email
from users.utils import send_email
from django.urls import reverse
from django.db.models import Q

import logging

logger = logging.getLogger(__name__)



@require_http_methods(["GET", "POST"])
def create_user(request):
    """Handle user registration"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        
        
        if not all([username, first_name, last_name, email, password]):
            messages.error(request, "All fields are required")
            return redirect("users:register")
        
        if len(password) < 8:
            messages.error(request,"Password must be at least 8 Characters")
            return redirect("users:register")
        
        if CustomUser.objects.filter(username=username).exists():
            messages.error(request, "Username already exists")
            return redirect("users:register")
        
      
        if CustomUser.objects.filter(email=email).exists():
            messages.error(request, "Email already exists")
            return redirect("users:register")
        
        try:
           
            user = CustomUser(
                username=username,
                email=email,
                last_name=last_name,
                first_name=first_name
            )
            
            user.validate_password(password)
            user.validate_user_email(email)
        
            user.set_password(password)
            user.save()
            
            Profile.objects.create(user=user)
            
            messages.success(request, "Account created successfully! Please log in.")
            return redirect("users:login")
            
        except ValidationError as e:
            error_message = e.messages[0] if hasattr(e, 'messages') else str(e)
            messages.error(request, error_message)
            return redirect("users:register")
        except Exception as e:
            messages.error(request, "An error occurred during registration. Please try again.")
            return redirect("users:register")
    
   
    return render(request, 'kelhub/index.html')


@require_http_methods(["GET", "POST"])
def login_user(request):
    """Handle user login"""
    
    if request.user.is_authenticated:
        if request.user.role == 'admin':
            return redirect('users:admin-dashboard')
        elif request.user.role == 'customer':
            return redirect('kelhub:dashboard')
        
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
      
        if not all([username, password]):
            messages.error(request, "Both username and password are required")
            return redirect("users:login")
        
     
        user = authenticate(request, username=username, password=password)
        
        if user is None:
            messages.error(request, "Invalid username or password")
            return redirect("users:login")

        login(request, user)
        messages.success(request, f"Welcome back, {user.first_name}!")
            
        if user.role == 'admin': # type: ignore
                return redirect("user:admin-dashboard")  
        elif user.role == 'customer': # type: ignore
                return redirect("kelhub:dashboard")
            
        else:
            messages.error(request, "Invalid username or password")
            return redirect("users:login")
  
    return render(request, 'kelhub/index.html')


@login_required
@require_http_methods(["GET", "POST"])
def change_password(request):
    """Handle password change for authenticated users"""
    if request.method == 'POST':
        current_password = request.POST.get('current_password', '')
        new_password = request.POST.get('new_password', '')
        confirm_password = request.POST.get('confirm_password', '')
        
        user = request.user
        if user.id != request.user.id:
            messages.error(request,"You are not authorized to perform this action")
            return redirect("user:login")
      
        if not all([current_password, new_password, confirm_password]):
            messages.error(request, "All fields are required")
            return redirect("users:change_password")
        
        user = request.user
        
        if not user.check_password(current_password):
            messages.error(request, "Current password is incorrect")
            return redirect("users:change_password")
    
        if new_password != confirm_password:
            messages.error(request, "New passwords do not match")
            return redirect("users:change_password")
        
        if current_password == new_password:
            messages.error(request, "New password must be different from current password")
            return redirect("users:change_password")
        
        try:
            user.validate_password(new_password)
        except ValidationError as e:
            error_message = e.messages[0] if hasattr(e, 'messages') else str(e)
            messages.error(request, error_message)
            return redirect("users:change_password")
        
        user.set_password(new_password)
        user.save()
        
    
        update_session_auth_hash(request, user)
        
        messages.success(request, "Password changed successfully!")
        if user.role == 'admin':
            return redirect('user:admin-dashboard')
        elif user.role == 'customer':
            return redirect('kelhub:dashboard') 
    return render(request, 'users/change_password.html')


@login_required
def logout_user(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect("users:login")

@login_required
def update_user_profile(request, user_id):
    """Update user profile information"""
    
    user = get_object_or_404(CustomUser, id=user_id)
    
    if request.user.id != user.id:
        messages.error(request, "You can only edit your own profile")
        return redirect("users:dashboard")
    

    profile, created = Profile.objects.get_or_create(user=user)
    
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        email = request.POST.get("email", "").strip()
        
        if not full_name:
            messages.error(request, "Full name is required")
            return redirect("users:edit_profile", user_id=user.id)
        
        if not email:
            messages.error(request, "Email is required")
            return redirect("users:edit_profile", user_id=user.id)
        
        if CustomUser.objects.filter(email=email).exclude(id=user.id).exists():
            messages.error(request, "Email is already taken by another user")
            return redirect("users:edit_profile", user_id=user.id)
        
        try:
            user.validate_user_email(email)
            
            user.full_name = full_name
            user.email = email
            user.save()
            
            # Update profile fields
            profile.phone_number = request.POST.get("phone_number", "").strip()
            profile.address = request.POST.get("address", "").strip()
            
            if request.FILES.get("avatar"):
                profile.avatar = request.FILES.get("avatar")
            
            profile.save()
            
            messages.success(request, "Profile updated successfully!")
            return redirect("users:dashboard")
            
        except ValidationError as e:
            error_message = e.messages[0] if hasattr(e, 'messages') else str(e)
            messages.error(request, error_message)
            return redirect("users:edit_profile", user_id=user.id)
        except Exception as e:
            messages.error(request, "An error occurred while updating your profile")
            return redirect("users:edit_profile", user_id=user.id)
    
    
    context = {
        'user': user,
        'profile': profile,
    }
    return render(request, 'users/edit_profile.html', context)

@require_http_methods(["GET", "POST"])
def reset_password_request(request):
    """Handle password reset request"""
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        
        if not email:
            messages.error(request, "Email is required")
            return redirect("users:reset_password_request")
        
        try:
            
            user = CustomUser.objects.get(email=email)
            
            ResetPasswordToken.objects.filter(user=user, is_used=False).update(is_used=True)
            
            reset_token = ResetPasswordToken.objects.create(user=user)
            logger.info(f"Reset token createed {reset_token}")
            
            reset_token.token = reset_token.generate_token()
            reset_token.save()
            
    
            reset_url = request.build_absolute_uri(
                reverse('users:reset_password', kwargs={'token': reset_token.token})
            )
            
           
            context = {
                'user': user,
                'reset_url': reset_url,
                'expiry_hours': 1,
            }
            
           
            send_email(
                subject='Password Reset Request - KELHUB',
                to_email=user.email,
                template_name='users/password_reset_email.html',
                context=context
            )
            logger.info(f"Sending password reset email to {user.email}")

            
            messages.success(request, "Password reset instructions have been sent to your email")
            return redirect("users:login")
            
        except CustomUser.DoesNotExist:
            messages.success(request, "If an account exists with that email, password reset instructions have been sent")
            return redirect("users:login")
        except Exception as e:
            logger.exception("Error sending password reset email")  
            messages.error(request, "An error occurred. Please try again later")
            return redirect("users:reset_password_request")
    

    return render(request, 'users/reset_password_request.html')


@require_http_methods(["GET", "POST"])
def reset_password(request, token):
    """Handle password reset with token"""
    try:
        reset_token = ResetPasswordToken.objects.get(token=token)
        
        is_valid, message = reset_token.is_valid()
        if not is_valid:
            messages.error(request, message)
            return redirect("users:reset_password_request")
        
        if request.method == 'POST':
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')
            
            if not new_password or not confirm_password:
                messages.error(request, "Both password fields are required")
                return redirect("users:reset_password", token=token)
            
            if new_password != confirm_password:
                messages.error(request, "Passwords do not match")
                return redirect("users:reset_password", token=token)
            
            if len(new_password) < 8:
                messages.error(request,"Password must be at least 8 characters")
            
            try:
                user = reset_token.user
                user.validate_password(new_password)
                
                user.set_password(new_password)
                user.save()
                
                # Mark token as used
                reset_token.is_used = True
                reset_token.save()
                        
                messages.success(request, "Password has been reset successfully. Please log in with your new password.")
                return redirect("users:login")
                
            except ValidationError as e:
                error_message = e.messages[0] if hasattr(e, 'messages') else str(e)
                messages.error(request, error_message)
                return redirect("users:reset_password", token=token)
        
        context = {'token': token}
        return render(request, 'users/reset_password.html', context)
        
    except ResetPasswordToken.DoesNotExist:
        messages.error(request, "Invalid or expired reset token")
        return redirect("users:reset_password_request")
    
@login_required
def admin_dashboard(request):
    return render(request,"users/admin_dashboard.html")



def display_data_plans_view(request, network):
    """
    Display available data plans for a network.
    """
    
    network_obj = get_object_or_404(Network,Q(key__iexact=network) | Q(name__icontains=network),is_active=True)
    data_bundles = DataBundle.objects.filter(network=network_obj,is_active=True).order_by('price')
    wallet = None
    if request.user.is_authenticated:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    context = {
        'network': network_obj,
        'data_bundles': data_bundles,
        'wallet': wallet,
    }
    
    return render(request, 'users/display_data_plans.html', context)


# @login_required
# def user_dashboard(request):
#     user = request.user
#     if user.id != request.user.id:
#         messages.error(request,"You are not authorized to perform this action")
        
#     wallet = Wallet.objects.filter(user=request.user).select_related("user")
#     return render(request,"users/user_dashboard.html")


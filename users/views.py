from django.shortcuts import render, redirect
from django.http import HttpResponse
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from .models import CustomUser, Profile


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


    return render(request, 'kelhub/index.html')


@require_http_methods(["GET", "POST"])
def login_user(request):
    """Handle user login"""
    if request.user.is_authenticated:
        return redirect("users:dashboard")  
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        
      
        if not all([username, password]):
            messages.error(request, "Both username and password are required")
            return redirect("users:login")
        
     
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, f"Welcome back, {user.first_name}!")
            
        if user.role == 'admin': # type: ignore
                return redirect("user:admin_dashboard")  
        elif user.role == 'customer': # type: ignore
                return redirect("users:dashboard")
            
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
        return redirect("users:dashboard") 
    return render(request, 'users/change_password.html')


@login_required
def logout_user(request):
    """Handle user logout"""
    logout(request)
    messages.success(request, "You have been logged out successfully")
    return redirect("users:login")
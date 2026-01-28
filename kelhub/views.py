from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import login_required
from .models import Network, DataBundle, Order, TransactionLog,Wallet,WalletTransaction
from .utils import get_data_plans, purchase_data, sync_data_bundles,validate_phone_number
from django.db import transaction

def home(request):
    """Homepage with network selection cards"""
    networks = Network.objects.filter(is_active=True)
    return render(request, 'kelhub/index.html', {'networks': networks})

@require_http_methods(["POST"])
def purchase_bundle(request, bundle_id):
    """Handle data bundle purchase"""
    bundle = get_object_or_404(DataBundle, id=bundle_id, is_active=True)
    phone_number = request.POST.get('phone_number')
    
    if not phone_number:
        messages.error(request, "Phone number is required")
        return redirect('kelhub:data_plans', network=bundle.network.key)
    
  
    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        network=bundle.network,
        bundle=bundle,
        recipient_phone=phone_number,
        amount=bundle.price,
        status='processing'
    )
    

    api_response = purchase_data(
        phone_number=phone_number,
        network=bundle.network.key,
        amount=float(bundle.price),
        capacity=bundle.capacity
    )
    
  
    TransactionLog.objects.create(
        order=order,
        request_payload={
            'phone_number': phone_number,
            'network': bundle.network.key,
            'amount': str(bundle.price),
            'capacity': bundle.capacity
        },
        response_payload=api_response,
        status_code=200 if api_response.get('status') == 'success' else 400
    )
    

    if api_response.get('status') == 'success':
        order.status = 'successful'
        order.api_order_id = api_response.get('order_id')
        order.api_reference = api_response.get('reference')
        messages.success(request, f"Successfully purchased {bundle.capacity} for {phone_number}")
    else:
        order.status = 'failed'
        messages.error(request, f"Purchase failed: {api_response.get('message', 'Unknown error')}")
    
    order.save()
    
    return redirect('kelhub:order_detail', order_id=order.id)


def order_detail(request, order_id):
    """View order details"""
    order = get_object_or_404(Order, id=order_id)
    
    
    if not request.user.is_staff:
        if not request.user.is_authenticated or order.user != request.user:
            messages.error(request, "You don't have permission to view this order")
            return redirect('kelhub:home')
    
    context = {
        'order': order,
    }
    
    return render(request, 'kelhub/order_detail.html', context)


def user_orders(request):
    """View user's order history"""
    if not request.user.is_authenticated:
        messages.warning(request, "Please login to view your orders")
        return redirect('login')
    
    orders = Order.objects.filter(user=request.user)
    
    context = {
        'orders': orders,
    }
    
    return render(request, 'kelhub/user_orders.html', context)

@login_required  # type: ignore
def wallet_view(request):
    """Display user's wallet and transaction history"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    transactions = WalletTransaction.objects.filter(wallet=wallet)[:20]
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
    }
    return render(request, 'kelhub/wallet.html', context)


@login_required
def deposit_view(request):
    """Handle wallet deposit"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            payment_method = request.POST.get('payment_method', 'mobile_money')
            payment_reference = request.POST.get('payment_reference', '')
            
            if amount <= 0:
                messages.error(request, 'Please enter a valid amount')
                return redirect('deposit')
            
            # Record balance before deposit
            balance_before = wallet.balance
            
            # In production, you would integrate with a payment gateway here
            # For now, we'll simulate a successful payment
            
            with transaction.atomic():
                # Deposit to wallet
                success, message = wallet.deposit(amount)
                
                if success:
                    # Create transaction record
                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type='deposit',
                        amount=amount,
                        payment_reference=payment_reference,
                        payment_method=payment_method,
                        status='completed',
                        description=f"Deposit via {payment_method}",
                        balance_before=balance_before,
                        balance_after=wallet.balance
                    )
                    
                    messages.success(request, f'Successfully deposited GH₵{amount} to your wallet')
                    return redirect('wallet')
                else:
                    messages.error(request, message)
                    
        except (ValueError, TypeError):
            messages.error(request, 'Invalid amount entered')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    context = {
        'wallet': wallet,
    }
    return render(request, 'kelhub/deposit.html', context)


def data_plans_view(request, network):
    """Display available data plans for a network"""
    network_obj = get_object_or_404(Network, key=network, is_active=True)
    
   
    data_bundles = DataBundle.objects.filter(network=network_obj, is_active=True).order_by('price')
    
    wallet = None
    if request.user.is_authenticated:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    context = {
        'network': network_obj,
        'data_bundles': data_bundles,
        'wallet': wallet,
    }
    
    return render(request, 'kelhub/data_plans.html', context)


@login_required
def purchase_data_view(request, bundle_id):
    """Handle data bundle purchase"""
    bundle = get_object_or_404(DataBundle, id=bundle_id, is_active=True)
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        recipient_phone = request.POST.get('recipient_phone', '').strip()
        payment_method = request.POST.get('payment_method', 'wallet')
        
        # Validate phone number
        if not recipient_phone:
            messages.error(request, 'Please enter a phone number')
            return redirect('purchase_data', bundle_id=bundle_id)
        
        if recipient_phone:
            validate_phone_number(recipient_phone)
        
        # Check wallet balance if paying with wallet
        if payment_method == 'wallet':
            if not wallet.can_purchase(bundle.price):
                messages.error(
                    request, 
                    f'Insufficient balance. You need GH₵{bundle.price} but only have GH₵{wallet.balance}. '
                    f'Please deposit GH₵{bundle.price - wallet.balance} more.'
                )
                return redirect('deposit')
        
        try:
            with transaction.atomic():
                # Create order
                order = Order.objects.create(
                    user=request.user,
                    network=bundle.network,
                    bundle=bundle,
                    recipient_phone=recipient_phone,
                    amount=bundle.price,
                    payment_method=payment_method,
                    status='pending'
                )
                
                # Process payment if using wallet
                if payment_method == 'wallet':
                    success, message = order.process_payment()
                    
                    if not success:
                        order.delete()
                        messages.error(request, message)
                        return redirect('purchase_data', bundle_id=bundle_id)
                
                # TODO: Call API to actually purchase the data
                # For now, mark as successful
                order.status = 'successful'
                order.save()
                
                messages.success(
                    request,
                    f'Successfully purchased {bundle.capacity} for {recipient_phone}. '
                    f'Remaining balance: GH₵{wallet.balance}'
                )
                return redirect('order_success', order_id=order.id)
                
        except Exception as e:
            messages.error(request, f'Purchase failed: {str(e)}')
            return redirect('purchase_data', bundle_id=bundle_id)
    
    context = {
        'bundle': bundle,
        'wallet': wallet,
    }
    return render(request, 'kelhub/purchase_data.html', context)


@login_required
def order_success_view(request, order_id):
    """Display order success page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    return render(request, 'kelhub/order_success.html', context)


@login_required
def order_history_view(request):
    """Display user's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    return render(request, 'kelhub/order_history.html', context)

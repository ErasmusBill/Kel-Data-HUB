from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.urls import reverse
from decimal import Decimal, InvalidOperation
from .models import Network, DataBundle, Order, TransactionLog, Wallet, WalletTransaction
from .utils import (
    get_data_plans, purchase_data, sync_data_bundles, validate_phone_number,
    initialize_paystack_payment, verify_paystack_payment, generate_guest_email
)


def home(request):
    """Homepage with network selection cards"""
    networks = Network.objects.filter(is_active=True)
    return render(request, 'kelhub/index.html', {'networks': networks})


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


def purchase_data_view(request, bundle_id):
    """
    Handle data bundle purchase - SUPPORTS GUESTS AND LOGGED-IN USERS
    Payment Methods: Wallet (logged-in only) or Paystack (guests + logged-in)
    """
    bundle = get_object_or_404(DataBundle.select_related('network'), id=bundle_id, is_active=True) # type: ignore
    
    
    wallet = None
    if request.user.is_authenticated:
        wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        recipient_phone = request.POST.get('recipient_phone', '').strip()
        payment_method = request.POST.get('payment_method', 'paystack')
        customer_email = request.POST.get('customer_email', '').strip()
    
        if not recipient_phone:
            messages.error(request, 'Please enter a phone number')
            return redirect('kelhub:purchase_data', bundle_id=bundle_id)
        
        validated_phone = validate_phone_number(recipient_phone)
        if not validated_phone:
            messages.error(
                request, 
                'Invalid phone number format. Please use: 0551234567 or +233551234567'
            )
            return redirect('kelhub:purchase_data', bundle_id=bundle_id)
        
        
        if not request.user.is_authenticated:
            payment_method = 'paystack'
            
           
            if not customer_email:
                customer_email = generate_guest_email(validated_phone)
        else:
            if not customer_email:
                customer_email = request.user.email or generate_guest_email(validated_phone)
        
        if payment_method == 'wallet':
            if not request.user.is_authenticated:
                messages.error(request, 'Please login to use wallet payment')
                return redirect('kelhub:purchase_data', bundle_id=bundle_id)
            
            if not wallet.can_purchase(bundle.price):
                shortfall = bundle.price - wallet.balance
                messages.error(
                    request, 
                    f'Insufficient balance. You need GH₵{bundle.price} but only have GH₵{wallet.balance}. '
                    f'Please deposit at least GH₵{shortfall} more.'
                )
                return redirect('kelhub:deposit')
        
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    user=request.user if request.user.is_authenticated else None,
                    network=bundle.network,
                    bundle=bundle,
                    phone_number=validated_phone,
                    amount=bundle.price,
                    payment_method=payment_method,
                    gateway='wallet' if payment_method == 'wallet' else 'paystack',
                    status='pending'
                )
                
                if payment_method == 'wallet' and request.user.is_authenticated:
                    success, message = order.process_payment()  # type: ignore
                    
                    if not success:
                        order.delete()
                        messages.error(request, f'Payment failed: {message}')
                        return redirect('kelhub:purchase_data', bundle_id=bundle_id)
                    
                   
                    success, api_message, response_data = order.process_api_purchase() # type: ignore
                    
                    if success:
                        messages.success(
                            request,
                            f'Successfully purchased {bundle.display_capacity} for {validated_phone}. '
                            f'Transaction Reference: {order.transaction_reference}'
                        )
                        wallet.refresh_from_db() # type: ignore
                        request.session['last_order_id'] = str(order.id)
                        return redirect('kelhub:order_success', order_id=order.id)
                    else:
                        messages.error(
                            request,
                            f'Purchase failed: {api_message}. Your money has been refunded.'
                        )
                        return redirect('kelhub:order_detail', order_id=order.id)
                
                elif payment_method == 'paystack':
                    callback_url = request.build_absolute_uri(
                        reverse('kelhub:paystack_callback')
                    )
                    
                    
                    metadata = {
                        'order_id': str(order.id),
                        'bundle': bundle.display_capacity,
                        'network': bundle.network.name,
                        'phone_number': validated_phone,
                        'user_id': str(request.user.id) if request.user.is_authenticated else 'guest'
                    }
                    
                    paystack_response = initialize_paystack_payment( # type: ignore
                        email=customer_email,
                        amount=bundle.price,
                        callback_url=callback_url,
                        reference=f"ORDER-{str(order.id)[:8]}",
                        metadata=metadata,
                        channels=['card', 'mobile_money', 'bank']
                    )
                    
                    if paystack_response.get('status') == 'success':
                
                        auth_url = paystack_response['data'].get('authorization_url')
                        access_code = paystack_response['data'].get('access_code')
                        paystack_ref = paystack_response['data'].get('reference')
                        
                        
                        order.transaction_reference = paystack_ref
                        order.api_response = paystack_response
                        order.status = 'processing'
                        order.save()
                        
                        
                        request.session['pending_order_id'] = str(order.id)
                        request.session['paystack_reference'] = paystack_ref
                        
                        
                        return redirect(auth_url)
                    else:
                        order.delete()
                        messages.error(
                            request,
                            f"Payment initialization failed: {paystack_response.get('message')}"
                        )
                        return redirect('kelhub:purchase_data', bundle_id=bundle_id)
                
        except Exception as e:
            messages.error(request, f'An unexpected error occurred: {str(e)}')
            return redirect('kelhub:purchase_data', bundle_id=bundle_id)
    
    context = {
        'bundle': bundle,
        'wallet': wallet,
        'is_guest': not request.user.is_authenticated,
    }
    return render(request, 'kelhub/purchase_data.html', context)


def paystack_callback(request):
    """
    Handle Paystack payment callback
    Verifies payment and processes data purchase
    """
    reference = request.GET.get('reference') or request.GET.get('trxref')
    
    if not reference:
        messages.error(request, 'Invalid payment reference')
        return redirect('kelhub:home')
    
    # Get order from session
    order_id = request.session.get('pending_order_id')
    
    if not order_id:
        messages.error(request, 'Order not found')
        return redirect('kelhub:home')
    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        messages.error(request, 'Order not found')
        return redirect('kelhub:home')
    
    # Verify payment with Paystack
    verification = verify_paystack_payment(reference)
    
    if verification.get('status') == 'success' and verification.get('verified'):
        # Payment successful
        verified_amount = verification.get('amount')
        
        # Verify amount matches
        if verified_amount != order.amount:
            order.status = 'failed'
            order.failure_reason = f"Amount mismatch: Expected {order.amount}, got {verified_amount}"
            order.save()
            
            messages.error(request, 'Payment verification failed: Amount mismatch')
            return redirect('kelhub:order_detail', order_id=order.id)
        
        # Update order with payment info
        order.transaction_reference = reference
        order.api_response = verification # type: ignore
        order.paid_from_wallet = False  # Paid via Paystack
        order.save()
        
        # Process data purchase via DataMart API
        success, api_message, response_data = order.process_api_purchase() # type: ignore
        
        if success:
            # Clear pending order from session
            if 'pending_order_id' in request.session:
                del request.session['pending_order_id']
            if 'paystack_reference' in request.session:
                del request.session['paystack_reference']
            
            # Store for tracking
            request.session['last_order_id'] = str(order.id)
            
            messages.success(
                request,
                f'Payment successful! {order.bundle.display_capacity} has been sent to {order.phone_number}'
            )
            return redirect('kelhub:order_success', order_id=order.id)
        else:
            order.status = 'failed'
            order.failure_reason = f"DataMart API Error: {api_message}"
            order.save()
            
            messages.error(
                request,
                f'Payment received but data delivery failed: {api_message}. '
                'Please contact support with your order ID for a refund.'
            )
            return redirect('kelhub:order_detail', order_id=order.id)
    else:
        # Payment failed or was cancelled
        order.status = 'failed'
        order.failure_reason = verification.get('message', 'Payment verification failed')
        order.save()
        
        messages.error(
            request,
            f"Payment failed: {verification.get('message', 'Unknown error')}"
        )
        return redirect('kelhub:order_detail', order_id=order.id)


def order_success_view(request, order_id):
    """Display order success page - WORKS FOR GUESTS AND LOGGED-IN USERS"""
    
    order = get_object_or_404(Order.select_related('network', 'bundle', 'user'), id=order_id) # type: ignore
    

    if request.user.is_authenticated:
        if not request.user.is_staff and order.user != request.user:
            messages.error(request, "You don't have permission to view this order")
            return redirect('kelhub:home')
    else:
     
        last_order_id = request.session.get('last_order_id')
        if str(order.id) != last_order_id:
            messages.error(request, "Order not found")
            return redirect('kelhub:home')
    
    wallet = None
    if request.user.is_authenticated and hasattr(request.user, 'wallet'):
        wallet = request.user.wallet
    
    context = {
        'order': order,
        'wallet': wallet,
        'is_guest': not request.user.is_authenticated,
    }
    return render(request, 'kelhub/order_success.html', context)


def order_detail(request, order_id):
    """View detailed order information - WORKS FOR GUESTS AND LOGGED-IN USERS"""
    
    order = get_object_or_404(Order.select_related('network', 'bundle', 'user'), id=order_id) # type: ignore

    if request.user.is_authenticated:
        if not request.user.is_staff and order.user != request.user:
            messages.error(request, "You don't have permission to view this order")
            return redirect('kelhub:home')
    else:
        session_order_id = request.session.get('last_order_id') or request.session.get('pending_order_id')
        if str(order.id) != session_order_id:
            messages.error(request, "Order not found")
            return redirect('kelhub:home')
    
  
    api_logs = None
    wallet_transactions = None
    
    if request.user.is_staff:
        api_logs = order.api_logs.all().order_by('-created_at')
        wallet_transactions = order.wallet_transactions.all().order_by('-created_at')
    
    context = {
        'order': order,
        'api_logs': api_logs,
        'wallet_transactions': wallet_transactions,
        'is_guest': not request.user.is_authenticated,
    }
    
    return render(request, 'kelhub/order_detail.html', context)



@login_required
def wallet_view(request):
    """Display user's wallet and transaction history"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    transactions = WalletTransaction.objects.filter(wallet=wallet).select_related('order').order_by('-created_at')[:50]
    
    pending_orders = Order.objects.filter(user=request.user,status='pending').count()
    
    successful_orders = Order.objects.filter(user=request.user,status='successful').count()
    
    context = {
        'wallet': wallet,
        'transactions': transactions,
        'pending_orders': pending_orders,
        'successful_orders': successful_orders,
    }
    return render(request, 'kelhub/wallet.html', context)


@login_required
def deposit_view(request):
    """Handle wallet deposit via Paystack"""
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        try:
            amount = Decimal(request.POST.get('amount', 0))
            
            if amount <= 0:
                messages.error(request, 'Please enter a valid amount greater than zero')
                return redirect('kelhub:deposit')
            
            if amount < Decimal('5.00'):
                messages.error(request, 'Minimum deposit is GH₵5.00')
                return redirect('kelhub:deposit')
            
            # Initialize Paystack payment for deposit
            callback_url = request.build_absolute_uri(
                reverse('kelhub:deposit_callback')
            )
            
            metadata = {
                'user_id': str(request.user.id),
                'wallet_id': str(wallet.id),
                'transaction_type': 'deposit'
            }
            
            paystack_response = initialize_paystack_payment(
                email=request.user.email or generate_guest_email(str(request.user.id)),
                amount=amount,
                callback_url=callback_url,
                reference=f"DEP-{wallet.id}-{int(amount * 100)}",
                metadata=metadata
            ) # type: ignore
            
            if paystack_response.get('status') == 'success':
                # Store amount and reference in session
                request.session['deposit_amount'] = str(amount)
                request.session['deposit_reference'] = paystack_response['data'].get('reference')
                
                # Redirect to Paystack
                return redirect(paystack_response['data'].get('authorization_url'))
            else:
                messages.error(
                    request,
                    f"Payment initialization failed: {paystack_response.get('message')}"
                )
                    
        except (ValueError, TypeError, InvalidOperation):
            messages.error(request, 'Invalid amount entered. Please enter a valid number.')
        except Exception as e:
            messages.error(request, f'An error occurred: {str(e)}')
    
    context = {
        'wallet': wallet,
    }
    return render(request, 'kelhub/deposit.html', context)


@login_required
def deposit_callback(request):
    """Handle Paystack callback for wallet deposits"""
    reference = request.GET.get('reference') or request.GET.get('trxref')
    
    if not reference:
        messages.error(request, 'Invalid payment reference')
        return redirect('kelhub:wallet')
    
    # Verify payment
    verification = verify_paystack_payment(reference)
    
    if verification.get('status') == 'success' and verification.get('verified'):
        amount = verification.get('amount')
        
        wallet, created = Wallet.objects.get_or_create(user=request.user)
        balance_before = wallet.balance
        
        with transaction.atomic():
            success, message = wallet.deposit(amount)
            
            if success:
                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type='deposit',
                    amount=amount,
                    payment_reference=reference,
                    payment_method='Paystack',
                    status='completed',
                    description=f'Wallet top-up via Paystack',
                    balance_before=balance_before,
                    balance_after=wallet.balance,
                    metadata=verification.get('metadata')
                )
                
                # Clear session
                if 'deposit_amount' in request.session:
                    del request.session['deposit_amount']
                if 'deposit_reference' in request.session:
                    del request.session['deposit_reference']
                
                messages.success(
                    request, 
                    f'Successfully deposited GH₵{amount} to your wallet. New balance: GH₵{wallet.balance}'
                )
            else:
                messages.error(request, message)
    else:
        messages.error(
            request,
            f"Deposit failed: {verification.get('message', 'Payment verification failed')}"
        )
    
    return redirect('kelhub:wallet')


@login_required
def order_history_view(request):
    """Display user's complete order history"""
    orders = Order.objects.filter(user=request.user).select_related('network', 'bundle').prefetch_related('wallet_transactions').order_by('-created_at')
    
    status_filter = request.GET.get('status')
    if status_filter and status_filter in dict(Order.STATUS_CHOICES):
        orders = orders.filter(status=status_filter)
    
    stats = {
        'total_orders': orders.count(),
        'successful': orders.filter(status='successful').count(),
        'failed': orders.filter(status='failed').count(),
        'pending': orders.filter(status='pending').count(),
        'refunded': orders.filter(status='refunded').count(),
    }
    
    context = {
        'orders': orders,
        'stats': stats,
        'status_filter': status_filter,
    }
    return render(request, 'kelhub/order_history.html', context)


@login_required
@require_http_methods(["POST"])
def retry_failed_order(request, order_id):
    """Retry a failed order"""
    old_order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if old_order.status != 'failed':
        messages.error(request, 'Can only retry failed orders')
        return redirect('kelhub:order_detail', order_id=order_id)
    
    request.session['retry_phone'] = old_order.phone_number
    return redirect('kelhub:purchase_data', bundle_id=old_order.bundle.id)



@require_http_methods(["GET"])
def check_wallet_balance(request):
    """AJAX endpoint to check wallet balance"""
    if not request.user.is_authenticated:
        return JsonResponse({
            'balance': 0,
            'formatted': 'GH₵0.00',
            'is_guest': True
        })
    
    wallet, created = Wallet.objects.get_or_create(user=request.user)
    
    return JsonResponse({
        'balance': float(wallet.balance),
        'formatted': f'GH₵{wallet.balance}',
        'is_guest': False
    })



def track_order(request):
    """Track order by order ID (for guests)"""
    order = None
    
    if request.method == 'POST':
        order_id = request.POST.get('order_id', '').strip()
        
        if order_id:
            try:
                order = Order.objects.select_related(
                    'network', 'bundle'
                ).get(id=order_id)
                
                request.session['tracked_order_id'] = str(order.id)
                
            except Order.DoesNotExist:
                messages.error(request, 'Order not found. Please check your Order ID.')
    
    context = {
        'order': order,
    }
    return render(request, 'kelhub/track_order.html', context)



@require_http_methods(["GET"])
def sync_bundles_view(request):
    """Manually sync data bundles from API (admin only)"""
    if not request.user.is_staff:
        messages.error(request, 'Permission denied')
        return redirect('kelhub:home')
    
    try:
        from .utils import sync_all_bundles
        
        results = sync_all_bundles()
        total_synced = sum(results.values())
        
        messages.success(
            request,
            f'Successfully synced {total_synced} bundles: ' + 
            ', '.join([f'{k}: {v}' for k, v in results.items()])
        )
    except Exception as e:
        messages.error(request, f'Sync failed: {str(e)}')
    
    return redirect('admin:index')
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from .models import Network, DataBundle, Order, TransactionLog
from .utils import get_data_plans, purchase_data, sync_data_bundles


def home(request):
    """Homepage with network selection cards"""
    networks = Network.objects.filter(is_active=True)
    return render(request, 'kelhub/index.html', {'networks': networks})


def data_plans_view(request, network):
    """Display available data plans for a network"""
    network_obj = get_object_or_404(Network, key=network, is_active=True)
    api_plans = get_data_plans(network)

    if api_plans:
        sync_data_bundles(network, network_obj)
    
    context = {
        'network': network_obj,
        'data_bundles': api_plans, 
    }
    
    return render(request, 'kelhub/data_plans.html', context)


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

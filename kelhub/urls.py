from django.urls import path
from . import views

app_name = 'kelhub'

urlpatterns = [
    # ========================================================================
    # PUBLIC VIEWS (No login required)
    # ========================================================================
    
    # Home
    path('', views.home, name='home'),
    
    # Data Plans
    path('plans/<str:network>/', views.data_plans_view, name='data_plans'),
    
    # Purchase (Works for guests and logged-in users)
    path('purchase/<int:bundle_id>/', views.purchase_data_view, name='purchase_data'),
    
    # Paystack Callback (Must be accessible without login)
    path('paystack/callback/', views.paystack_callback, name='paystack_callback'),
    
    # Order Views (Guests can view via session)
    path('order/<uuid:order_id>/', views.order_detail, name='order_detail'),
    path('order/<uuid:order_id>/success/', views.order_success_view, name='order_success'),
    
    # Track Order
    path('track/', views.track_order, name='track_order'),
    
    # AJAX Endpoints
    path('api/wallet/balance/', views.check_wallet_balance, name='check_balance'),
    
    # ========================================================================
    # AUTHENTICATED VIEWS (Login required)
    # ========================================================================
    
    # Wallet
    path('wallet/', views.wallet_view, name='wallet'),
    path('wallet/deposit/', views.deposit_view, name='deposit'),
    path('wallet/deposit/callback/', views.deposit_callback, name='deposit_callback'),
    
    # Order Management
    path('order/<uuid:order_id>/retry/', views.retry_failed_order, name='retry_order'),
    path('orders/', views.order_history_view, name='order_history'),
    
    # ========================================================================
    # ADMIN/UTILITY (Staff only)
    # ========================================================================
    
    path('admin/sync-bundles/', views.sync_bundles_view, name='sync_bundles'),
]
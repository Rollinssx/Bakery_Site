# base/admin_urls.py
from django.urls import path
from . import admin_views

app_name = 'admin'

urlpatterns = [
    path('dashboard/', admin_views.admin_dashboard, name='dashboard'),
    path('orders/', admin_views.admin_orders, name='orders'),
    path('orders/<int:order_id>/', admin_views.admin_order_detail, name='order_detail'),
    path('orders/<int:order_id>/update/', admin_views.admin_update_order_status, name='update_order_status'),
    path('products/', admin_views.admin_products, name='products'),
    path('customers/', admin_views.admin_customers, name='customers'),
    path('messages/', admin_views.admin_messages, name='messages'),
    path('settings/', admin_views.admin_settings, name='settings'),
]

# Add these to your main base/urls.py:
#
# from django.urls import path, include
# from . import admin_urls
#
# urlpatterns = [
#     # ... your existing patterns
#     path('admin-panel/', include(admin_urls, namespace='admin')),
# ]



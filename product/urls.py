from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),  # List products
    path('create/', views.create_product, name='create_product'),  # Create product
    path('update/<int:id>/', views.update_product, name='update_product'),  # Update product
    path('delete/<int:id>/', views.delete_product, name='delete_product'),  # Delete product
    path('export-products/', views.export_products_to_excel, name='export_products'),
]

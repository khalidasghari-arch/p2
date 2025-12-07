import pandas as pd
from django.http import HttpResponse
from django.core.paginator import Paginator
from django.shortcuts import render, redirect
from .models import Product
from .forms import ProductForm
from hiva.models import Criteria

def criteria_table_view(request):
    criteria = Criteria.objects.select_related(
        'standardfk__sectionfk__areafk', 'scorefk'
    )
    return render(request, 'criteria_table.html', {'criteria_list': criteria})

# Create view
def create_product(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm()
    return render(request, 'create_product.html', {'form': form})

# Read view (List products)
def product_list(request):
    products = Product.objects.all()

    # Set up pagination
    paginator = Paginator(products, 5)  # Show 5 products per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'product_list.html', {'page_obj': page_obj})

# Update view
def update_product(request, id):
    product = Product.objects.get(id=id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            return redirect('product_list')
    else:
        form = ProductForm(instance=product)
    return render(request, 'update_product.html', {'form': form})

# Delete view
def delete_product(request, id):
    product = Product.objects.get(id=id)
    if request.method == 'POST':
        product.delete()
        return redirect('product_list')
    return render(request, 'delete_product.html', {'product': product})

# export all the data excel file format
def export_products_to_excel(request):
    # Query your model for all data
    products = Product.objects.all()

    # Create a list of dictionaries to convert into a DataFrame
    data = []
    for product in products:
        data.append({
            "Name": product.name,
            "Price": product.price,
            "Description": product.description,
            "Category": product.category
        })

    # Create a DataFrame from the data
    df = pd.DataFrame(data)

    # Create an Excel writer and write the DataFrame to an Excel file
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=products.xlsx'

    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Products', index=False)

    return response


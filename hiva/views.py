from django.shortcuts import render
from .models import Standards, Section

def display_tables(request):
    # Query all entries from Table1 and join with related data from Table2 and Table3
    data = Standards.objects.prefetch_related('Section').all()

    context = {
        'data': data,
    }
    return render(request, 'display_tables.html', context)
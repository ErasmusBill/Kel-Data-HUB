from django.shortcuts import render
from .utils import purchase_data, get_data_plans
# Create your views here.

def home(request):
    return render(request, 'kelhub/index.html')
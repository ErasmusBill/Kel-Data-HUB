from django.shortcuts import render
from .utils import purchase_data, get_data_plans
# Create your views here.

def home(request):
    return render(request, 'kelhub/index.html')


def get_all_data_plans(request, network):
    data_plans = get_data_plans(network) # type: ignore
    plans = ["MTN", "AIRTELTIGO", "TELECEL"]
    for newtwork in plans:
        if network == newtwork:
            data_plans = get_data_plans(network) # type: ignore
    return render(request, 'kelhub/data_plans.html', {'data_plans': data_plans})


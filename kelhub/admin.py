from django.contrib import admin
from .models import *
from kelhub.models import TransactionLog
# Register your models here.

admin.site.register(Network)
admin.site.register(DataBundle)
admin.site.register(Order)
admin.site.register(TransactionLog)
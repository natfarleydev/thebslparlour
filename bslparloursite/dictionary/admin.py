from django.contrib import admin

# Register your models here.

from .models import BSLEntry, EnglishEntry

admin.site.register(BSLEntry)
admin.site.register(EnglishEntry)

from django.db import models
from django.utils import timezone

# Create your models here.

class RequestedSign(models.Model):
    short_description = models.CharField(max_length=100)
    description = models.TextField()
    date_added = models.DateTimeField(default=timezone.now, editable=False)
    
    def __str__(self):
        return self.short_description+" ("+self.description+")"

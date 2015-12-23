from django.db import models
from django.utils import timezone

# Create your models here.

class RequestedSign(models.Model):
    gloss = models.CharField(max_length=100)
    description = models.TextField()
    date_added = models.DateTimeField(default=timezone.now, editable=False)
    
    def __unicode__(self):
        return self.gloss+"("+self.description+")"

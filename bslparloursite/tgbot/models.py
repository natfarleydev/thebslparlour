from django.db import models
from django.utils import timezone

from videolibrary.models import SourceVideo

# Create your models here.

# TODO consider whether this is needed anymore
class RequestedSign(models.Model):
    short_description = models.CharField(max_length=100)
    description = models.TextField()
    date_added = models.DateTimeField(default=timezone.now, editable=False)
    
    def __str__(self):
        return self.short_description+" ("+self.description+")"

class TelegramGif(models.Model):
    file_id = models.CharField(max_length=200) # TODO change to telegram's max length
    source_video = models.ForeignKey(SourceVideo)

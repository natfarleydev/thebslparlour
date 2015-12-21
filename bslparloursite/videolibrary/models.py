from django.db import models
from django.utils import timezone
from sizefield.models import FileSizeField

# Create your models here.

class Video(models.Model):
    sha224 = models.CharField(max_length=56, unique=True)
    filename = models.CharField(max_length=200)
    dropbox_directory = models.CharField(max_length=200)
    mime_type = models.CharField(max_length=200)
    date_added = models.DateTimeField(default=timezone.now, editable=False)
    size = FileSizeField()
    
    class Meta:
        abstract = True

    def __unicode__(self):
        return self.filename or self.sha224_id

class SourceVideo(Video):
    vimeo_uri = models.IntegerField()
    youtube_id = models.CharField(max_length=30, blank=True)

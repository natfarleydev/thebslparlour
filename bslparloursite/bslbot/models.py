from django.db import models
from dictionary.models import BSLEntry

# Create your models here.

class Tweet(models.Model):
    """Base class for a tweet."""
    tweet = models.CharField(max_length=135)
    suggested_tweet = models.CharField(max_length=136, blank=True)
    last_tweeted = models.DateTimeField(blank=True)

    def __str__(self):
        return self.tweet
    
    class Meta:
        abstract = True
        

class InfoTweet(Tweet):
    """This class is purely for tweeting information.

    This tweet is empty because it is identical to Tweet, but it has a
    (potentially) different admin interface."""
    pass


class BSLDictionaryTweet(Tweet):
    """BSLDictionary entry tweet model."""
    bsl_entry = models.ForeignKey(BSLEntry)

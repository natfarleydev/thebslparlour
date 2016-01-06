from django.db import models
from videolibrary.models import SourceVideo

# Create your models here.

class EnglishEntry(models.Model):
    word = models.CharField(max_length=50)
    word_index = models.IntegerField(help_text=(
        'A unique integer to make sure words with the same name are uniquely identifiable'
    ))
    description = models.CharField(max_length=140, help_text=(
        'Describe the word in 140 characters or less.'
    ))
    example_sentence = models.CharField(max_length=140, blank=True, help_text=(
        'An example sentence in 140 characters or less.'
    ))
    # This is linked via ManyToManyField with BSLEntry

    class Meta:
        unique_together = ('word', 'word_index')

    def __str__(self):
       return self.word+" "+str(self.word_index)


class BSLEntry(models.Model):
    """Simple model for BSL dictionary entry."""
    # source_videos_sha224 = models.CharField(max_length=56, help_text=(
    #     'The sha224 id of the bslparlour source video for this BSL entry.'
    # ))
    source_videos = models.ManyToManyField(SourceVideo)
    gloss = models.CharField(max_length=50, help_text='A gloss of the sign e.g. CAKE.')
    gloss_index = models.IntegerField(help_text=(
        'A unique integer to make sure glosses with the same name are uniquely identifiable'
    ))
    level_choices = (
        ('unclassified', 'Unclassified'),
        ('basic', 'Basic'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('nearnative', 'Near-native+'),
        ('specialistlds', 'Specialist (LDS)'),
        ('specialistchristian', 'Specialist (Christian)'),
    )
    level = models.CharField(max_length=30, choices=level_choices, default='unclassified')
    example_glossed_phrase = models.CharField(max_length=200, blank=True, help_text=(
        'An example of a phrase where this sign would be used, e.g. ME CAKE EAT'
    ))
    english_entries = models.ManyToManyField(EnglishEntry, blank=True)

    def has_add_permission(self):
        return True

    def __str__(self):
        return self.gloss + ' ' + str(self.gloss_index)
        
    class Meta:
        unique_together = ('gloss', 'gloss_index')

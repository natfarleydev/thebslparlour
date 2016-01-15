from django.contrib import admin
from .models import BSLDictionaryTweet, InfoTweet

# Register your models here.

class NotChangedTweetFilter(admin.SimpleListFilter):
    title = "processing status"
    
    parameter_name = "processing_status"

    def lookups(self, request, model_admin):
        return (
            ('unprocessed', 'Unprocessed'),
            ('needs_approval', 'Needs approval'),
        )
        

    def queryset(self, request, queryset):
        if self.value() == "unprocessed":
            return queryset.filter(tweet__contains="glossed", suggested_tweet__contains="glossed")
        elif self.value() == "needs_approval":
            return queryset.filter(tweet__contains="glossed").exclude(suggested_tweet__contains="glossed")


class TweetAdmin(admin.ModelAdmin):
    list_display = ('tweet', 'suggested_tweet')
    list_filter = (NotChangedTweetFilter,)
    list_display_links = ('suggested_tweet',)
    list_editable = ('tweet',)
    search_fields = ('tweet',)
    

    save_as = True
    save_on_top = True

admin.site.register(BSLDictionaryTweet, TweetAdmin)
admin.site.register(InfoTweet, TweetAdmin)

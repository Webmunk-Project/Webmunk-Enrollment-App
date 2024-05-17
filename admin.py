# pylint: disable=no-member, line-too-long

from django.contrib.admin.filters import RelatedFieldListFilter, AllValuesFieldListFilter
from django.contrib.gis import admin
from django.urls import reverse
from django.utils.safestring import mark_safe
from django.utils import timezone

from .models import Enrollment, EnrollmentGroup, ExtensionRuleSet, ScheduledTask, \
                    RuleMatchCount, PageContent, ArchivedExtensionRuleSet, AmazonPurchase, \
                    AmazonReward, AmazonASINItem

class DropdownRelatedFilter(RelatedFieldListFilter):
    template = 'admin/enrollment_task_enrollment_dropdown_filter.html'

class DropdownSlugListFilter(AllValuesFieldListFilter):
    template = 'admin/enrollment_task_enrollment_dropdown_filter.html'

class ScheduledTaskInline(admin.TabularInline):
    model = ScheduledTask

    fields = ['task', 'slug', 'active', 'completed', 'last_check']

    show_change_link = True

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None): # pylint: disable=arguments-differ,unused-argument
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(Enrollment)
class EnrollmentAdmin(admin.OSMGeoAdmin):
    list_display = ('assigned_identifier', 'group', 'enrolled', 'rule_set', 'issues', 'last_fetched', 'contact_after',)
    list_filter = ('group', 'enrolled', 'last_fetched', 'contact_after', 'rule_set', )

    search_fields = ('assigned_identifier',)

    inlines = [
        ScheduledTaskInline,
    ]

@admin.register(EnrollmentGroup)
class EnrollmentGroupAdmin(admin.OSMGeoAdmin):
    list_display = ('name',)

    search_fields = ('name',)

@admin.register(ExtensionRuleSet)
class ExtensionRuleSetAdmin(admin.OSMGeoAdmin):
    list_display = ('name', 'is_active', 'is_default',)
    list_filter = ('is_active', 'is_default',)

    search_fields = ('name', 'rule_json')

@admin.register(ArchivedExtensionRuleSet)
class ArchivedExtensionRuleSetAdmin(admin.OSMGeoAdmin):
    list_display = ('rule_set', 'active_until',)
    list_filter = ('active_until', 'rule_set',)

    search_fields = ('rule_set__name', 'rule_json')

def reset_scheduled_task_completions(modeladmin, request, queryset): # pylint: disable=unused-argument, invalid-name
    queryset.update(completed=None)

reset_scheduled_task_completions.description = 'Reset scheduled task completions'

def complete_scheduled_tasks(modeladmin, request, queryset): # pylint: disable=unused-argument, invalid-name
    queryset.update(completed=timezone.now())

complete_scheduled_tasks.description = 'Mark selected tasks as completed'

@admin.register(ScheduledTask)
class ScheduledTaskAdmin(admin.OSMGeoAdmin):
    list_display = ('enrollment', 'slug', 'task', 'active', 'last_check', 'completed')
    list_filter = ('active', 'completed', 'last_check', ('slug', DropdownSlugListFilter), ('enrollment', DropdownRelatedFilter))

    search_fields = ('task', 'slug', 'url',)
    actions = [reset_scheduled_task_completions, complete_scheduled_tasks]

@admin.register(RuleMatchCount)
class RuleMatchCountAdmin(admin.OSMGeoAdmin):
    list_display = ('url', 'pattern', 'matches', 'checked', 'content_length',)
    list_filter = ('checked', 'url', 'pattern',)
    readonly_fields = ['page_content',]

    search_fields = ('url', 'pattern',)

@admin.register(PageContent)
class PageContentAdmin(admin.OSMGeoAdmin):
    list_display = ('url', 'retrieved',)
    list_filter = ('retrieved', 'url')

    search_fields = ('url', 'content',)

    readonly_fields = ['rule_match_links',]

    def rule_match_links(self, obj): # pylint: disable=no-self-use
        links = []

        for link in obj.rule_matches.all().order_by('checked'):
            links.append('<a href="%s">%s</a>' % (reverse('admin:%s_%s_change' % ('enrollment', 'rulematchcount'), args=[link.id]), link))

        return mark_safe('<br />'.join(links)) # nosec

    rule_match_links.short_description = 'Rule matches'

@admin.register(AmazonPurchase)
class AmazonPurchaseAdmin(admin.OSMGeoAdmin):
    list_display = ('enrollment', 'purchase_date', 'item_name', 'item_type',)
    list_filter = ('item_type', 'purchase_date', 'enrollment',)

    search_fields = ('item_type', 'item_name', 'item_url',)

@admin.register(AmazonReward)
class AmazonRewardAdmin(admin.OSMGeoAdmin):
    list_display = ('participant', 'item_type', 'item_name', 'item_price',)
    list_filter = ('item_type', 'participant')

    search_fields = ('participant', 'item_type', 'item_name', 'item_url',)

@admin.register(AmazonASINItem)
class AmazonASINItemAdmin(admin.OSMGeoAdmin):
    list_display = ('asin', 'item_name', 'fetch_item_type', 'fetch_brand', 'fetch_category', 'fetch_category_ids', 'fetched',)
    list_filter = ('fetched',)

    search_fields = ('asin', 'item_name', 'keepa_response',)

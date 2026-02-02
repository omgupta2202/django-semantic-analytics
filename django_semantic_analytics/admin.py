from django.contrib import admin
from django import forms
from .models import SemanticAtom, VerifiedQuery, FailedQuery

@admin.register(SemanticAtom)
class SemanticAtomAdmin(admin.ModelAdmin):
    list_display = ('name', 'atom_type', 'created_at')
    list_filter = ('atom_type',)
    search_fields = ('name', 'description')
    filter_horizontal = ('dependencies',)
    readonly_fields = ('created_at', 'updated_at')

@admin.register(VerifiedQuery)
class VerifiedQueryAdmin(admin.ModelAdmin):
    list_display = ('question', 'created_at')
    search_fields = ('question', 'sql_query')

@admin.register(FailedQuery)
class FailedQueryAdmin(admin.ModelAdmin):
    list_display = ('question', 'error_message', 'created_at')
    readonly_fields = ('question', 'attempted_sql', 'error_message', 'created_at')
    actions = ['approve_as_verified']

    def approve_as_verified(self, request, queryset):
        """
        Custom action to quickly move a fixed query to the Verified layer.
        """
        for failed in queryset:
            if failed.attempted_sql:
                VerifiedQuery.objects.get_or_create(
                    question=failed.question,
                    defaults={'sql_query': failed.attempted_sql}
                )
        self.message_user(request, "Selected queries have been moved to Verified Queries.")
    
    approve_as_verified.short_description = "Approve attempted SQL as Verified Query"

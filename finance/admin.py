from django.contrib import admin

from .models import Assessment, FeePolicy, Payment


@admin.register(FeePolicy)
class FeePolicyAdmin(admin.ModelAdmin):
    list_display = ('tuition_per_unit', 'registration_fee', 'technology_fee', 'updated_at')

    def has_add_permission(self, request):
        return not FeePolicy.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ('student', 'term', 'units', 'tuition', 'registration_fee', 'technology_fee')
    list_filter = ('term',)
    search_fields = ('student__student_id', 'student__user__username')
    readonly_fields = ('student', 'term', 'units', 'tuition_per_unit', 'tuition', 'registration_fee', 'technology_fee')


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'assessment', 'amount', 'received_at', 'recorded_by')
    list_filter = ('received_at',)
    search_fields = ('reference', 'assessment__student__student_id')
    readonly_fields = ('reference', 'assessment', 'amount', 'received_at', 'recorded_by', 'note')

from django.contrib import admin
from .models import (
    Technician,
    Task,
    TaskAssignment,
    Report,
    AuditLog
)

# =========================
# TECHNICIAN
# =========================

@admin.register(Technician)
class TechnicianAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'role', 'can_manage_all')
    list_filter = ('role', 'can_manage_all')
    search_fields = ('user__username', 'phone')


# =========================
# TASK
# =========================

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'status',
        'location',
        'created_by',
        'created_at',
        'is_visible'
    )

    list_filter = ('status', 'is_visible', 'created_at')
    search_fields = ('title', 'location')
    ordering = ('-created_at',)

    readonly_fields = ('created_at', 'completed_at')


# =========================
# TASK ASSIGNMENT
# =========================

@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'task',
        'technician',
        'role',
        'has_validated_participation',
        'assigned_at',
        'validated_at'
    )

    list_filter = ('role', 'has_validated_participation')
    search_fields = (
        'task__title',
        'technician__user__username'
    )

    readonly_fields = ('assigned_at', 'validated_at')


# =========================
# REPORT
# =========================

@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'task',
        'author',
        'created_at',
        'is_locked',
        'is_archived'
    )

    list_filter = ('is_locked', 'is_archived', 'created_at')
    search_fields = (
        'task__title',
        'author__user__username'
    )

    readonly_fields = ('created_at',)

    def has_delete_permission(self, request, obj=None):
        # Interdire suppression si archivé
        if obj and obj.is_archived:
            return False
        return True


# =========================
# AUDIT LOG
# =========================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'action',
        'object_type',
        'object_id',
        'timestamp'
    )

    list_filter = ('action', 'object_type')
    search_fields = ('user__username',)
    ordering = ('-timestamp',)

    # Logs = lecture seule
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

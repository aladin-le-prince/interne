from django.db import models
from django.contrib.auth.models import User


class Technician(models.Model):
    ROLE_CHOICES = [
        ('TECHNICIAN', 'Technicien'),
        ('SUPERVISOR', 'Superviseur'),
        ('SUPERADMIN', 'SuperviseurAdmin'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=20)
    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='TECHNICIAN'
    )

    can_manage_all = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    
    
    
    
class Task(models.Model):
    STATUS_CHOICES = [
        ('CREATED', 'Créée'),
        ('ASSIGNED', 'Assignée'),
        ('IN_PROGRESS', 'En cours'),
        ('AWAITING_VALIDATION', 'En attente validation admin'),
        ('COMPLETED', 'Validée (finie)'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=255)

    created_by = models.ForeignKey(
        Technician,
        on_delete=models.SET_NULL,
        null=True,
        related_name='tasks_created'
    )

    estimated_duration = models.DurationField(
        help_text="Durée estimée pour l'exécution de la tâche"
    )

    status = models.CharField(
        max_length=30,
        choices=STATUS_CHOICES,
        default='CREATED'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    is_visible = models.BooleanField(
        default=True,
        help_text="Visible dans les dashboards opérationnels"
    )

    def __str__(self):
        return self.title

class TaskAssignment(models.Model):
    ROLE_CHOICES = [
        ('AUTHOR', 'Auteur du rapport'),
        ('PARTICIPANT', 'Participant'),
    ]

    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    technician = models.ForeignKey(Technician, on_delete=models.CASCADE)

    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    has_validated_participation = models.BooleanField(default=False)

    assigned_at = models.DateTimeField(auto_now_add=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('task', 'technician')

    def __str__(self):
        return f"{self.task} - {self.technician} ({self.role})"

      
    
    
class Report(models.Model):
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='reports'
    )

    author = models.ForeignKey(
        Technician,
        on_delete=models.CASCADE
    )

    work_done = models.TextField()
    observations = models.TextField()

    photo = models.ImageField(upload_to='reports/photos/')
    created_at = models.DateTimeField(auto_now_add=True)

    is_locked = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)

    def __str__(self):
        return f"Rapport {self.id} - {self.task.title}"

    
    

    
    
class AuditLog(models.Model):
    # Utilisateur ayant effectué l'action
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)

    # Action réalisée (création, consultation, export, etc.)
    action = models.CharField(max_length=255)

    # Objet concerné (Task, Report, etc.)
    object_type = models.CharField(max_length=100)
    object_id = models.IntegerField()

    # Date et heure exactes
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} - {self.action} - {self.timestamp}"
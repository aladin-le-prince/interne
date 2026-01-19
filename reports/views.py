from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import HttpResponseForbidden, HttpResponse
from django.core.paginator import Paginator
from django.template.loader import get_template
from django.utils import timezone
from xhtml2pdf import pisa
from datetime import timedelta
from .models import Task, TaskAssignment, Report, Technician, AuditLog
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse

 

# =========================
# UTILITAIRES / SÉCURITÉ
# =========================

def is_supervisor(user):
    return hasattr(user, 'technician') and user.technician.role in ['SUPERVISOR', 'SUPERADMIN']

def is_technician(user):
    return hasattr(user, 'technician') and user.technician.role == 'TECHNICIAN'

def is_superadmin(user):
    return hasattr(user, 'technician') and user.technician.role == 'SUPERADMIN'


def log_action(user, action, obj):
    AuditLog.objects.create(
        user=user,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=obj.id
    )


def render_to_pdf(template_src, context_dict):
    template = get_template(template_src)
    html = template.render(context_dict)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="rapport.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response


# =========================
# TECHNICIENS (SUPERADMIN)
# =========================

@login_required
def create_technician(request):
    if not is_superadmin(request.user):
        return HttpResponseForbidden("Accès refusé")

    if request.method == 'POST':
        if User.objects.filter(username=request.POST['username']).exists():
            return render(request, 'reports/create_technician.html', {'error': "Utilisateur déjà existant"})

        user = User.objects.create_user(
            username=request.POST['username'],
            password=request.POST['password']
        )

        Technician.objects.create(
            user=user,
            phone=request.POST['phone'],
            role=request.POST['role']
        )
        return redirect('dashboard')

    return render(request, 'reports/create_technician.html')


@login_required
def edit_technician(request, tech_id):
    if not is_superadmin(request.user):
        return HttpResponseForbidden()

    technician = get_object_or_404(Technician, id=tech_id)

    if request.method == 'POST':
        technician.phone = request.POST.get('phone')
        technician.role = request.POST.get('role')
        technician.save()
        return redirect('dashboard')

    return render(request, 'reports/edit_technician.html', {'technician': technician})


@login_required
def delete_technician(request, tech_id):
    if not is_superadmin(request.user):
        return HttpResponseForbidden()

    technician = get_object_or_404(Technician, id=tech_id)

    if request.method == 'POST':
        technician.user.delete()
        return redirect('dashboard')

    return render(request, 'reports/delete_technician.html', {'technician': technician})


# =========================
# DASHBOARD
# =========================

@login_required
def dashboard(request):
    tech = request.user.technician

    context = {
        'role': tech.role,
        'is_superadmin': tech.role == 'SUPERADMIN',
        'is_supervisor': tech.role in ['SUPERVISOR', 'SUPERADMIN'],
    }

    # Tasks et rapports selon rôle
    if tech.role == 'SUPERADMIN':
        context.update({
            'tasks': Task.objects.exclude(status='COMPLETED').prefetch_related('taskassignment_set__technician'),
            'technicians': Technician.objects.all(),
            'reports': Report.objects.order_by('-created_at')[:10],
        })
    elif tech.role == 'SUPERVISOR':
        context.update({
            'tasks': Task.objects.exclude(status='COMPLETED').prefetch_related('taskassignment_set__technician'),
            'technicians': Technician.objects.all(),
            'reports': Report.objects.order_by('-created_at')[:10],
        })
    else:  # TECHNICIAN
        assigned_tasks = TaskAssignment.objects.filter(
            technician=tech,
            task__status__in=['CREATED', 'ASSIGNED', 'IN_PROGRESS', 'AWAITING_VALIDATION']
        ).select_related('task')
        context.update({
            'tasks': [ta.task for ta in assigned_tasks],
            'reports': Report.objects.filter(author=tech, is_archived=False).order_by('-created_at'),
        })

    # Définir couleurs par rôle pour badges
    role_colors = {
        'TECHNICIAN': '#0d6efd',  # bleu
        'SUPERVISOR': '#dc3545',  # rouge
        'SUPERADMIN': '#6f42c1',  # violet
    }
    if 'technicians' in context:
        for t in context['technicians']:
            t.role_color = role_colors.get(t.role, '#6c757d')

    return render(request, 'new-design/dashboard.html', context)



# =========================
# TÂCHES
# =========================

@login_required
def task_list(request):
    if not is_supervisor(request.user):
        return HttpResponseForbidden()

    tasks = Task.objects.all()
    status = request.GET.get('status')
    if status == 'closed':
        tasks = tasks.filter(status='COMPLETED')
    elif status == 'active':
        tasks = tasks.exclude(status='COMPLETED')

    return render(request, 'reports/task_list.html', {'tasks': tasks})


@login_required
def task_detail(request, pk):
    task = get_object_or_404(Task, pk=pk)
    reports = Report.objects.filter(task=task).order_by('-created_at')
    assignments = TaskAssignment.objects.filter(task=task).select_related('technician')
    return render(request, 'reports/task_detail.html', {'task': task, 'reports': reports, 'assignments': assignments})


@login_required
def technician_tasks(request, tech_id):
    if not is_supervisor(request.user):
        return HttpResponseForbidden()

    technician = get_object_or_404(Technician, id=tech_id)
    assigned_tasks = TaskAssignment.objects.filter(
        technician=technician,
        task__status__in=['CREATED', 'ASSIGNED', 'IN_PROGRESS', 'AWAITING_VALIDATION']
    ).select_related('task')

    return render(request, 'reports/technician_tasks.html', {
        'technician': technician,
        'tasks': [ta.task for ta in assigned_tasks]
    })


@login_required
def assign_task(request, task_id):
    # Vérification rôle
    if not (is_superadmin(request.user) or is_supervisor(request.user)):
        return HttpResponseForbidden()

    # Récupération de la tâche
    task = get_object_or_404(Task, id=task_id)

    # Liste des techniciens disponibles
    technicians = Technician.objects.all()

    if request.method == 'POST':
        tech_id = request.POST.get('technician')
        technician = get_object_or_404(Technician, id=tech_id)

        # Création de l'assignation si elle n'existe pas
        TaskAssignment.objects.get_or_create(
            task=task,
            technician=technician,
            role='PARTICIPANT'
        )
        log_action(request.user, f"Assignation tâche à {technician.user.username}", task)
        return redirect('task_detail', pk=task.id)

    return render(request, 'reports/assign_task.html', {
        'task': task,
        'technicians': technicians
    })


@login_required
def close_task(request, task_id):
    if not is_superadmin(request.user):
        return HttpResponseForbidden()

    task = get_object_or_404(Task, id=task_id)
    task.status = 'COMPLETED'
    task.completed_at = timezone.now()
    task.save()
    log_action(request.user, "Clôture tâche", task)
    return redirect('task_list')



@csrf_exempt
@login_required
def update_task_status(request):
    if request.method == 'POST' and is_supervisor(request.user):
        data = json.loads(request.body)
        task_id = data.get('id')
        new_status = data.get('status')
        task = get_object_or_404(Task, id=task_id)
        task.status = new_status
        task.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'Forbidden'}, status=403)

@login_required
def task_create(request):
    if not (is_supervisor(request.user) or is_superadmin(request.user)):
        return HttpResponseForbidden("Accès refusé")

    if request.method == 'POST':
        duration_str = request.POST.get('estimated_duration')

        # Conversion HH:MM:SS -> timedelta
        try:
            hours, minutes, seconds = map(int, duration_str.split(':'))
            estimated_duration = timedelta(
                hours=hours,
                minutes=minutes,
                seconds=seconds
            )
        except Exception:
            return render(request, 'reports/task_create.html', {
                'error': "Durée invalide. Format attendu : HH:MM:SS"
            })

        Task.objects.create(
            title=request.POST.get('title'),
            description=request.POST.get('description'),
            location=request.POST.get('location'),
            estimated_duration=estimated_duration,
            created_by=request.user.technician,
            status='CREATED'
        )

        return redirect('dashboard')

    return render(request, 'reports/task_create.html')




# =========================
# RAPPORTS
# =========================

@login_required
def report_create(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    tech = request.user.technician

    if not TaskAssignment.objects.filter(task=task, technician=tech).exists():
        return HttpResponseForbidden()

    if request.method == 'POST':
        if 'photo' not in request.FILES:
            return render(request, 'reports/report_create.html', {'task': task, 'error': "Photo obligatoire"})

        report = Report.objects.create(
            task=task,
            author=tech,
            work_done=request.POST['work_done'],
            observations=request.POST['observations'],
            photo=request.FILES['photo'],
            is_locked=True
        )
        log_action(request.user, "Soumission rapport", report)
        return redirect('task_detail', pk=task.id)

    return render(request, 'reports/report_create.html', {'task': task})


@login_required
def report_list(request):
    if not is_supervisor(request.user):
        return HttpResponseForbidden()

    paginator = Paginator(Report.objects.order_by('-created_at'), 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    return render(request, 'reports/report_list.html', {'page_obj': page_obj})


@login_required
def report_detail(request, pk):
    report = get_object_or_404(Report, pk=pk)
    log_action(request.user, "Consultation rapport", report)
    return render(request, 'reports/report_detail.html', {'report': report})


@login_required
def report_pdf(request, pk):
    report = get_object_or_404(Report, pk=pk)

    if not (is_supervisor(request.user) or report.author == request.user.technician):
        return HttpResponseForbidden()

    log_action(request.user, "Export PDF", report)
    return render_to_pdf('reports/report_pdf.html', {'report': report})


@login_required
def technician_reports(request, tech_id):
    if not is_supervisor(request.user):
        return HttpResponseForbidden()

    technician = get_object_or_404(Technician, id=tech_id)
    reports = Report.objects.filter(author=technician).order_by('-created_at')
    return render(request, 'reports/technician_reports.html', {'technician': technician, 'reports': reports})


# =========================
# ARCHIVAGE & AUDIT
# =========================

@login_required
def archive_report(request, pk):
    if not is_supervisor(request.user):
        return HttpResponseForbidden()

    report = get_object_or_404(Report, pk=pk)
    report.is_archived = True
    report.save()
    log_action(request.user, "Archivage rapport", report)
    return redirect('report_list')


@login_required
def archived_reports(request):
    if not is_supervisor(request.user):
        return HttpResponseForbidden()

    reports = Report.objects.filter(is_archived=True)
    return render(request, 'reports/archived_reports.html', {'reports': reports})


@login_required
def audit_log_list(request):
    if not is_superadmin(request.user):
        return HttpResponseForbidden()

    logs = AuditLog.objects.order_by('-timestamp')[:500]
    return render(request, 'reports/audit_log_list.html', {'logs': logs})

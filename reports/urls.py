from django.urls import path
from .import views 
from django.contrib.auth import views as auth_views
urlpatterns = [
    path('', auth_views.LoginView.as_view(
        template_name='reports/login.html'
    ), name='login'),

    path('dashboard/', views.dashboard, name='dashboard'),
    
    path('dashboard/update-task-status/', views.update_task_status, name='update_task_status'),


    path('task/', views.task_list, name='task_list'),
    path('task/<int:pk>/', views.task_detail, name='task_detail'),
    path('task/create/', views.task_create, name='task_create'),


    path('reports/new/<int:task_id>/', views.report_create, name='report_create'),
    path('reports/', views.report_list, name='report_list'),
    path('reports/<int:pk>/', views.report_detail, name='report_detail'),
    path('reports/<int:pk>/pdf/', views.report_pdf, name='report_pdf'),

    path('reports/<int:pk>/archive/', views.archive_report, name='archive_report'),
    path('reports/archives/', views.archived_reports, name='archived_reports'),

    path('audit/', views.audit_log_list, name='audit_log'),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # ---- TECHNICIENS (ADMIN / SUPERVISOR) ----
    path('technician/create/', views.create_technician, name='create_technician'),
    path('technician/<int:tech_id>/tasks/', views.technician_tasks, name='technician_tasks'),
    path('technician/<int:tech_id>/reports/', views.technician_reports, name='technician_reports'),
    path('technician/<int:task_id>/assign_task/', views.assign_task, name='assign_task'),
    path('technician/<int:tech_id>/edit/', views.edit_technician, name='edit_technician'),
    path('technician/<int:tech_id>/delete/', views.delete_technician, name='delete_technician'),
]





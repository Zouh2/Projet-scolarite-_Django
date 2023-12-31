from django.shortcuts import render, redirect
from django.http import HttpResponse
from members.models import Member
import csv
import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from django.http import HttpResponse
import datetime
from .models import GenerateReportForm
from django.db.models import Q
from notifications.config import get_notification_count

# Create your views here.
def export_all(user_obj):
    # Create a response object
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="users.pdf"'

    # Create a PDF object using ReportLab
    pdf = SimpleDocTemplate(response, pagesize=letter)

    # Define the style of the table
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 14),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])

    # Create a list to hold all the data
    data = [['First name', 'Last name', 'DOB', 'Mobile', 'Admission Date', 'Class']]

    # Fetch values from the user object and append to the data list
    members = user_obj.values_list('first_name', 'last_name', 'dob', 'mobile_number', 'admitted_on',
                                   'subscription_type')
    for user in members:
        data.append(list(user))

    # Create the table and apply the style
    table = Table(data)
    table.setStyle(style)

    # Add table to the PDF
    elements = []
    elements.append(table)

    # Build PDF
    pdf.build(elements)

    return response

def reports(request):
    if request.method == 'POST':
        form = GenerateReportForm(request.POST)
        if form.is_valid():
            if request.POST.get('month') and request.POST.get('year') :
                query = Q(
                    registration_date__month=request.POST.get('month'),
                    registration_date__year=request.POST.get('year'),

                )
            elif request.POST.get('month') and request.POST.get('year'):
                query = Q(
                    registration_date__month=request.POST.get('month'),
                    registration_date__year=request.POST.get('year')
                )
            elif request.POST.get('month'):
                query = Q(
                    registration_date__month=request.POST.get('month'),

                )
            elif request.POST.get('year'):
                query = Q(
                    registration_date__year=request.POST.get('year'),
                )
            else:
                query = Q(
                    registration_date__year=request.POST.get('year'),
                )
            users = Member.objects.filter(query)
            # aggregate_amount = 0
            # for member in users:
            #     aggregate_amount += member.amount
            if 'export' in request.POST:
                return export_all(users)
            context = {
                'users': users,
                'form': form,
                # 'aggregate_amount': aggregate_amount,
                # 'students_registered': len(reg_users),
                'subs_end_today_count': get_notification_count(),
            }
            return render(request, 'reports.html', context)
    else:
        form = GenerateReportForm()
    return render(request, 'reports.html', {'form': form, 'subs_end_today_count': get_notification_count(),})

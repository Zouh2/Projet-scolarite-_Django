from django.shortcuts import render, redirect, reverse
from django.http import JsonResponse
from django.core import serializers
from .models import AddMemberForm, Member, SearchForm, UpdateMemberGymForm, UpdateMemberInfoForm
import datetime, csv
from django.http import HttpResponse
import dateutil.relativedelta as delta
import dateutil.parser as parser
from datetime import datetime
from django.core.files.storage import FileSystemStorage
from payments.models import Payments
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from notifications.config import get_notification_count
from django.db.models.signals import post_save
from notifications.config import my_handler
from django.contrib import messages
import time

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors


from django.conf import settings
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from django.http import HttpResponse
import os

from reportlab.lib.units import inch
import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from django.http import HttpResponse
import datetime
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from django.http import HttpResponse
import datetime
def model_save(model):
    post_save.disconnect(my_handler, sender=Member)
    model.save()
    post_save.connect(my_handler, sender=Member)

def check_status(request, object):
    object.stop = 1 if request.POST.get('stop') == '1' else 0
    return object

# Export user information.
def export_all(user_obj):
    response = HttpResponse(content_type='application/pdf')

    # Create a PDF object using ReportLab
    pdf = SimpleDocTemplate(response, pagesize=A4)

    # Create a list to hold all elements
    elements = []

    # Add a title
    styles = getSampleStyleSheet()
    title_style = styles['Title']
    elements.append(Paragraph("recu  de payement ", title_style))

    # Add a spacer
    elements.append(Spacer(1, 12))

    # Get the first user's information
    first_user = user_obj.first()

    # Check if the user has a photo
    if first_user.photo:
        # Construct the absolute path to the user's image
        user_image_path = os.path.join(settings.MEDIA_ROOT, str(first_user.photo))

        # Add user's image if the file exists
        if os.path.exists(user_image_path):
            elements.append(Image(user_image_path, width=1.5 * inch, height=1.5 * inch))

    # Add user's information in a paragraph format
    current_timestamp = time.time()

    current_date = time.strftime('%d-%m-%Y %H:%M:%S', time.localtime(current_timestamp))
    data = [
        ["Nom:", f"{first_user.first_name} {first_user.last_name}"],
        ["Genre:", first_user.genre],
        ["Mobile:", first_user.mobile_number],
        ["Date d'admission:", first_user.admitted_on.strftime('%d-%m-%Y')],
        ["Type d'abonnement:", first_user.subscription_type],
        ["Date d'impression:", current_date]
    ]

    # Créer le tableau
    table = Table(data)

    # Appliquer un style au tableau
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Couleur de fond pour l'en-tête
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Couleur du texte pour l'en-tête
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # Centrer le contenu
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),  # Police en gras pour l'en-tête
        ('FONTSIZE', (0, 0), (-1, 0), 12),  # Taille de police pour l'en-tête
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),  # Espacement au bas de l'en-tête
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),  # Couleur de fond pour les autres cellules
        ('GRID', (0, 0), (-1, -1), 1, colors.black)  # Lignes du tableau
    ]))

    # Ajouter le tableau à la liste des éléments
    elements.append(table)

    # Build PDF
    pdf.build(elements)

    # Set filename in Content-Disposition
    filename = f"{first_user.first_name}_{first_user.last_name}_attestation.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    return response

def members(request):
    form = AddMemberForm()
    context = {
        'form': form,
        'subs_end_today_count': get_notification_count(),
    }
    return render(request, 'add_member.html', context)

def view_member(request):
    view_all = Member.objects.filter(stop=0).order_by('first_name')
    paginator = Paginator(view_all, 100)
    try:
        page = request.GET.get('page', 1)
        view_all = paginator.page(page)
    except PageNotAnInteger:
        view_all = paginator.page(1)
    except EmptyPage:
        view_all = paginator.page(paginator.num_pages)
    search_form = SearchForm()

    stopped = Member.objects.filter(stop=1).order_by('first_name')
    context = {
        'all': view_all,
        'stopped': stopped,
        'search_form': search_form,
        'subs_end_today_count': get_notification_count(),
    }
    return render(request, 'view_member.html', context)

def add_member(request):
    view_all = Member.objects.all()
    success = 0
    member = None
    if request.method == 'POST':
        form = AddMemberForm(request.POST, request.FILES)
        if form.is_valid():
            temp = form.save(commit=False)
            temp.first_name = request.POST.get('first_name').capitalize()
            temp.last_name = request.POST.get('last_name').capitalize()
            temp.filiere = request.POST.get('filiere').capitalize()
            temp.genre = request.POST.get('genre').capitalize()
            temp.registration_upto = parser.parse(request.POST.get('registration_date')) + delta.relativedelta(months=int(request.POST.get('subscription_period')))
            if request.POST.get('fee_status') == 'pending':
                temp.notification = 1

            model_save(temp)
            success = 'Successfully Added Member'

            # Add payments if payment is 'paid'
            if temp.fee_status == 'paid':
                payments = Payments(
                                    user=temp,
                                    payment_date=temp.registration_date,
                                    payment_period=temp.subscription_period,
                                    payment_amount=temp.amount)
                payments.save()

            form = AddMemberForm()
            member = Member.objects.last()

        context = {
            'add_success': success,
            'form': form,
            'member': member,
            'subs_end_today_count': get_notification_count(),
        }
        return render(request, 'add_member.html', context)
    else:
        form = AddMemberForm()
        context = {
            'form': form,
            'subs_end_today_count': get_notification_count(),
        }
    return render(request, 'add_member.html', context)


def search_member(request):
    if request.method == 'POST':
        if 'clear' in request.POST:
            return redirect('view_member')
        search_form = SearchForm(request.POST)
        result = None  # Change this to None as initially no result is found
        if search_form.is_valid():
            full_name = request.POST.get('search')  # Assuming you enter full name in search box
            # Split the full name into first and last names
            first_name, last_name = full_name.split(' ', 1) if ' ' in full_name else (full_name, '')

            # Search by full name (both first and last names)
            result = Member.objects.filter(first_name__icontains=first_name.capitalize(),
                                           last_name__icontains=last_name.capitalize())

        view_all = Member.objects.all()

        context = {
            'all': view_all,
            'search_form': search_form,
            'result': result,
            'subs_end_today_count': get_notification_count(),
        }
        return render(request, 'view_member.html', context)
    else:
        search_form = SearchForm()
    return render(request, 'view_member.html', {'search_form': search_form})


def delete_member(request, id):
    print(id)
    Member.objects.filter(pk=id).delete()
    return redirect('view_member')

def update_member(request, id):
    if request.method == 'POST' and request.POST.get('export'):
        return export_all(Member.objects.filter(pk=id))
    if request.method == 'POST' and request.POST.get('no'):
        return redirect('/')
    if request.method == 'POST' and request.POST.get('gym_membership'):
            gym_form = UpdateMemberGymForm(request.POST)
            if gym_form.is_valid():
                object = Member.objects.get(pk=id)
                amount = request.POST.get('amount')
                day = (parser.parse(request.POST.get('registration_upto')) - delta.relativedelta(months=int(request.POST.get('subscription_period')))).day
                last_day = parser.parse(str(object.registration_upto)).day

                month = parser.parse(request.POST.get('registration_upto')).month
                last_month = parser.parse(str(object.registration_upto)).month
                # if status is stopped then do not update anything
                if object.stop == 1 and not request.POST.get('stop') == '0' and request.POST.get('gym_membership'):
                    messages.error(request, 'Please start the status of user to update the record')
                    return redirect('update_member', id=object.pk)

                elif (object.genre != request.POST.get('genre')):
                    object.genre = request.POST.get('genre')
                    object = check_status(request, object)
                    model_save(object)

                # check if user has modified only the date
                elif (datetime.datetime.strptime(str(object.registration_date), "%Y-%m-%d") != datetime.datetime.strptime(request.POST.get('registration_date'), "%Y-%m-%d")):
                        object.registration_date =  parser.parse(request.POST.get('registration_date'))
                        object.registration_upto =  parser.parse(request.POST.get('registration_date')) + delta.relativedelta(months=int(request.POST.get('subscription_period')))
                        object.fee_status = request.POST.get('fee_status')
                        object = check_status(request, object)
                        model_save(object)
                # if amount and period are changed
                elif (object.amount != amount) and (object.subscription_period != request.POST.get('subscription_period')):
                    object.subscription_type =  request.POST.get('subscription_type')
                    object.subscription_period =  request.POST.get('subscription_period')
                    object.registration_date =  parser.parse(request.POST.get('registration_upto'))
                    object.registration_upto =  parser.parse(request.POST.get('registration_upto')) + delta.relativedelta(months=int(request.POST.get('subscription_period')))
                    object.fee_status = request.POST.get('fee_status')
                    object.amount =  request.POST.get('amount')
                    object = check_status(request, object)
                    model_save(object)
                # if only subscription_period is Changed
                elif (object.subscription_period != request.POST.get('subscription_period')):
                    object.subscription_period =  request.POST.get('subscription_period')
                    object = check_status(request, object)
                    model_save(object)
                # if amount and type are changed
                elif (object.amount != amount) and (object.subscription_type != request.POST.get('subscription_type')):
                    object.subscription_type =  request.POST.get('subscription_type')
                    object.subscription_period =  request.POST.get('subscription_period')
                    object.registration_date =  parser.parse(request.POST.get('registration_upto'))
                    object.registration_upto =  parser.parse(request.POST.get('registration_upto')) + delta.relativedelta(months=int(request.POST.get('subscription_period')))
                    object.fee_status = request.POST.get('fee_status')
                    object.amount =  request.POST.get('amount')
                    object = check_status(request, object)
                    model_save(object)
                # if amount ad fee status are changed
                elif (object.amount != amount) and ((request.POST.get('fee_status') == 'paid') or (request.POST.get('fee_status') == 'pending')):
                        object.amount = amount
                        object.fee_status = request.POST.get('fee_status')
                        object = check_status(request, object)
                        model_save(object)
                # if only amount is channged
                elif (object.amount != amount):
                    object.registration_date =  parser.parse(request.POST.get('registration_upto'))
                    object.registration_upto =  parser.parse(request.POST.get('registration_upto')) + delta.relativedelta(months=int(request.POST.get('subscription_period')))
                    object.fee_status = request.POST.get('fee_status')
                    object.amount =  request.POST.get('amount')
                    if request.POST.get('fee_status') == 'pending':
                        object.notification =  1
                    elif request.POST.get('fee_status') == 'paid':
                        object.notification = 2
                    object = check_status(request, object)
                    model_save(object)
                # nothing is changed
                else:
                    if not request.POST.get('stop') == '1':
                        object.registration_date =  parser.parse(request.POST.get('registration_upto'))
                        object.registration_upto =  parser.parse(request.POST.get('registration_upto')) + delta.relativedelta(months=int(request.POST.get('subscription_period')))
                        object.amount =  request.POST.get('amount')
                        if request.POST.get('fee_status') == 'pending':
                            object.notification =  1
                        elif request.POST.get('fee_status') == 'paid':
                            object.notification = 2
                    object.fee_status = request.POST.get('fee_status')
                    object = check_status(request, object)
                    model_save(object)

                # Add payments if payment is 'paid'
                if object.fee_status == 'paid':
                    check = Payments.objects.filter(
                        payment_date=object.registration_date,
                        user__pk=object.pk).count()
                    if check == 0:
                        payments = Payments(
                                            user=object,
                                            payment_date=object.registration_date,
                                            payment_period=object.subscription_period,
                                            payment_amount=object.amount)
                        payments.save()
                user = Member.objects.get(pk=id)
                gym_form = UpdateMemberGymForm(initial={
                                        'registration_date': user.registration_date,
                                        'registration_upto': user.registration_upto,
                                        'subscription_type': user.subscription_type,
                                        'subscription_period': user.subscription_period,
                                        'amount': user.amount,
                                        'fee_status': user.fee_status,
                                         'genre': user.genre,
                                        'stop': user.stop,
                                        })

                info_form = UpdateMemberInfoForm(initial={
                                        'first_name': user.first_name,
                                        'last_name': user.last_name,
                                         'genre' : user.genre,
                                        'dob': user.dob,
                                        })

                try:
                    payments = Payments.objects.filter(user=user)
                except Payments.DoesNotExist:
                    payments = 'No Records'
                messages.success(request, 'Record updated successfully!')
                return redirect('update_member', id=user.pk)
            else:
                user = Member.objects.get(pk=id)
                info_form = UpdateMemberInfoForm(initial={
                                        'first_name': user.first_name,
                                        'last_name': user.last_name,
                                         'genre': user.genre,
                                        'dob': user.dob,
                                        })

                try:
                    payments = Payments.objects.filter(user=user)
                except Payments.DoesNotExist:
                    payments = 'No Records'
                return render(request,
                    'update.html',
                    {
                        'payments': payments,
                        'gym_form': gym_form,
                        'info_form': info_form,
                        'user': user,
                        'subs_end_today_count': get_notification_count(),
                    })
    elif request.method == 'POST' and request.POST.get('info'):
        object = Member.objects.get(pk=id)
        object.first_name = request.POST.get('first_name')
        object.last_name = request.POST.get('last_name')
        object.dob = request.POST.get('dob')

        # for updating photo
        if 'photo' in request.FILES:
            myfile = request.FILES['photo']
            fs = FileSystemStorage(base_url="")
            photo = fs.save(myfile.name, myfile)
            object.photo = fs.url(photo)
        model_save(object)

        user = Member.objects.get(pk=id)
        gym_form = UpdateMemberGymForm(initial={
                                'registration_date': user.registration_date,
                                'registration_upto': user.registration_upto,
                                'subscription_type': user.subscription_type,
                                'subscription_period': user.subscription_period,
                                'amount': user.amount,
                                'fee_status': user.fee_status,
                                'genre': user.genre,
                                'stop': user.stop,
                                })

        info_form = UpdateMemberInfoForm(initial={
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                 'genre': user.genre,
                                'dob': user.dob,
                                })

        try:
            payments = Payments.objects.filter(user=user)
        except Payments.DoesNotExist:
            payments = 'No Records'

        return render(request,
            'update.html',
            {
                'payments': payments,
                'gym_form': gym_form,
                'info_form': info_form,
                'user': user,
                'updated': 'Record Updated Successfully',
                'subs_end_today_count': get_notification_count(),
            })
    else:
        user = Member.objects.get(pk=id)

        if len(Payments.objects.filter(user=user)) > 0:
            payments = Payments.objects.filter(user=user)
        else:
            payments = 'No Records'
        gym_form = UpdateMemberGymForm(initial={
                                'registration_date': user.registration_date,
                                'registration_upto': user.registration_upto,
                                'subscription_type': user.subscription_type,
                                'subscription_period': user.subscription_period,
                                'amount': user.amount,
                                'fee_status': user.fee_status,
                                'genre': user.genre,
                                'stop': user.stop,
                                })

        info_form = UpdateMemberInfoForm(initial={
                                'first_name': user.first_name,
                                'last_name': user.last_name,
                                 'genre': user.genre,
                                'dob': user.dob,
                                })
        return render(request,
                        'update.html',
                        {
                            'payments': payments,
                            'gym_form': gym_form,
                            'info_form': info_form,
                            'user': user,
                            'subs_end_today_count': get_notification_count(),
                        }
                    )

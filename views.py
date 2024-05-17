# pylint: disable=line-too-long, no-member

import csv
import datetime
import decimal
import io
import json
import re
import traceback

import chardet

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.http import HttpResponse, Http404
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from simple_data_export.models import ReportJob

from .models import Enrollment, EnrollmentGroup, ExtensionRuleSet, ScheduledTask, AmazonReward
from .simple_data_export_api import compile_data_export

@csrf_exempt
def enroll(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    payload = {}

    now = timezone.now()

    if raw_identifier is not None:
        raw_identifier = raw_identifier.strip().lower()

        found_enrollment = None

        for enrollment in Enrollment.objects.all().order_by('assigned_identifier'):
            if raw_identifier in (enrollment.current_raw_identifier().strip().lower(), enrollment.assigned_identifier,):
                found_enrollment = enrollment

                break

        if found_enrollment is None:
            # found_enrollment = Enrollment(enrolled=now, last_fetched=now)

            # found_enrollment.assign_random_identifier(raw_identifier)
            # found_enrollment.save()

            payload = {
              'identifier': '00000000',
              'rules': {
                'actions': {},
                'additional-css': [],
                'description': [
                  'Enrollment in this study is now closed.',
                  'Please uninstall the extension by clicking the link below.'
                ],
                'pending-tasks-label': 'Please complete these tasks.',
                'filters': [],
                'key': 'Qhvrmhxp9spERvawGPLozqnPhYgKoYjfTJv2CPQVqyk=',
                'rules': [],
                'log-elements': [],
                'upload-url': 'https://server-q.webmunk.org/data/add-bundle.json',
                'enroll-url': 'https://enroll.webmunk.org/enroll/enroll.json',
                'uninstall-url': 'https://enroll.webmunk.org/enroll/uninstall?identifier=<IDENTIFIER>',
                'tasks': [
                  {
                    'message': 'Uninstall Study Browser Extension',
                    'url': 'https://chrome.google.com/webstore/detail/study-browser-extension/koijebmgmlpeinmgdfogdoflpjfigcmi'
                  }
                ]
              }
            }

            return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

        else:
            found_enrollment.last_fetched = now
            found_enrollment.save()

        payload['identifier'] = found_enrollment.assigned_identifier

        payload['rules'] = {
            'rules': [],
            'additional-css': [],
            'actions': {},
        }

        try:
            settings.WEBMUNK_ASSIGN_RULES(found_enrollment, ExtensionRuleSet)
        except AttributeError:
            if found_enrollment.rule_set is None:
                selected_rules = ExtensionRuleSet.objects.filter(is_default=True).first()

                if selected_rules is not None:
                    found_enrollment.rule_set = selected_rules
                    found_enrollment.save()

        try:
            settings.WEBMUNK_UPDATE_TASKS(found_enrollment, ScheduledTask)
        except AttributeError:
            traceback.print_exc()

        if found_enrollment.rule_set is not None and found_enrollment.rule_set.is_active:
            payload['rules'] = found_enrollment.rule_set.rules()

            tasks = []

            now = timezone.now()

            for task in found_enrollment.tasks.filter(completed=None, active__lte=now).order_by('active'):
                tasks.append({
                    'message': task.task,
                    "url": task.url
                })

            payload['rules']['tasks'] = tasks
        else:
            payload['error'] = 'Participant not configured with ruleset and no default ruleset selected.'
    else:
        payload['error'] = 'Unable to retrieve original raw identifier from the request. Please fix and try again.'

    try:
        settings.WEBMUNK_UPDATE_ALL_RULE_SETS(payload)
    except AttributeError:
        pass

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@csrf_exempt
def uninstall(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    now = timezone.now()

    if raw_identifier is not None:
        found_enrollment = None

        for enrollment in Enrollment.objects.all():
            if raw_identifier in (enrollment.current_raw_identifier(), enrollment.assigned_identifier,):
                found_enrollment = enrollment

                break

        if found_enrollment is not None:
            found_enrollment.last_uninstalled = now
            found_enrollment.save()

    return render(request, 'webmunk_uninstall.html')

@csrf_exempt
def amazon_fetched(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    # TODO - Add additional metadata about how data looks from extension.

    payload = {
        'updated': 0
    }

    if raw_identifier is not None:
        now = timezone.now()

        for enrollment in Enrollment.objects.all():
            if raw_identifier in (enrollment.current_raw_identifier(), enrollment.assigned_identifier,):
                payload['updated'] += enrollment.tasks.filter(slug__icontains='amazon-fetch', completed=None, active__lte=now).update(completed=now)

                # if enrollment.tasks.filter(slug__icontains='amazon-fetch').exclude(completed=None).count() > 1 and enrollment.tasks.filter(slug='main-survey-final').count() == 0:
                #    survey_url = 'https://hbs.qualtrics.com/jfe/form/SV_37xQ9ZpbqC75UVg?webmunk_id=%s' % enrollment.assigned_identifier

                #    ScheduledTask.objects.create(enrollment=enrollment, active=(now + datetime.timedelta(days=3)), task='Complete Final Survey', slug='main-survey-final', url=survey_url)

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@csrf_exempt
def mark_eligible(request): # pylint: disable=too-many-branches
    raw_identifier = request.POST.get('identifier', request.GET.get('identifier', None))

    if raw_identifier is not None:
        now = timezone.now()

        for enrollment in Enrollment.objects.all():
            if raw_identifier in (enrollment.current_raw_identifier(), enrollment.assigned_identifier,):
                metadata = enrollment.fetch_metadata()

                is_eligible = metadata.get('is_eligible', False)

                if is_eligible is False:
                    metadata['is_eligible'] = now.isoformat()

                    enrollment.metadata = json.dumps(metadata, indent=2)
                    enrollment.save()

    return render(request, 'webmunk_eligible.html')


@csrf_exempt
def privacy(request): # pylint: disable=too-many-branches
    return render(request, 'webmunk_privacy.html')

@staff_member_required
def enrollments(request):
    context = {
        'enrollments': Enrollment.objects.all().order_by('-enrolled'),
        'groups': EnrollmentGroup.objects.all().order_by('name'),
    }

    return render(request, 'webmunk_enrollments.html', context=context)

def unsubscribe_reminders(request, identifier):
    context = {}

    later = timezone.now() + datetime.timedelta(days=(365 * 250))

    Enrollment.objects.filter(assigned_identifier=identifier).update(contact_after=later)

    return render(request, 'webmunk_unsubscribe_reminders.html', context=context)

def update_group(request):
    payload = {
        'message': 'Group not updated.'
    }

    if request.method == 'POST':
        identifier = request.POST.get('identifier', None)
        group = request.POST.get('group', None)

        enrollment = Enrollment.objects.filter(assigned_identifier=identifier).first()
        group = EnrollmentGroup.objects.filter(name=group).first()

        if enrollment is not None:
            enrollment.group = group
            enrollment.save()

            payload['message'] = 'New group for %s: %s' % (enrollment, group)

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@staff_member_required
def enrollments_txt(request): # pylint: disable=unused-argument, too-many-branches, too-many-statements
    filename = compile_data_export('enrollment.enrollments', [])

    if filename is not None:
        with open(filename, 'rb') as open_file:
            response = HttpResponse(open_file, content_type='text/csv', status=200)
            response['Content-Disposition'] = 'attachment; filename= "webmunk-enrollments.txt"'

            return response

    raise Http404

@staff_member_required
def enrollment_upload_rewards(request): # pylint: disable=unused-argument, too-many-branches, too-many-statements, too-many-locals
    payload = {
        'message': 'Error uploading file.'
    }

    if request.method == 'POST':
        input_file = request.FILES['purchase_upload']

        added = 0

        raw_data = input_file.read()

        result = chardet.detect(raw_data)

        input_file.seek(0)

        with io.TextIOWrapper(input_file, encoding=result['encoding']) as text_file:
            csv_in = csv.DictReader(text_file)

            for row in csv_in:
                identifier = row['webmunk_id']
                wishlist_url = row['webmunk_id']
                item_url = row['url_purchased']
                item_name = row['product_title_purchased']

                item_price = row.get('price_item_purchased', '')
                item_type = row.get('item_purchased', None)

                notes = row.get('study_notes', None)

                if item_name.strip() != '':
                    enrollment = Enrollment.objects.filter(assigned_identifier=identifier).first()

                    if enrollment is not None:
                        reward = AmazonReward.objects.filter(participant=enrollment, item_url=item_url).first()

                        if reward is None:
                            reward = AmazonReward(participant=enrollment, item_url=item_url)

                            reward.wishlist_url = wishlist_url
                            reward.item_type = item_type
                            reward.item_name = item_name

                            stripped_price = re.sub(r'[^\d.]', '', item_price)

                            if stripped_price != '':
                                float_price = float(decimal.Decimal(stripped_price))

                                reward.item_price = float_price

                            reward.notes = notes

                            reward.save()

                            added += 1

        payload['message'] = '%d items added.' % added

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@staff_member_required
def enrollments_rewards_json(request): # pylint: disable=unused-argument, too-many-branches, too-many-statements
    payload = {}

    identifier = request.GET.get('webmunk_id', '')

    enrollment = Enrollment.objects.filter(assigned_identifier=identifier).first()

    if enrollment is not None:
        reward_index = 1

        for reward in enrollment.rewards.all():
            payload['full_name_product%d' % reward_index] = reward.item_name

            payload['asin_product%d' % reward_index] = reward.fetch_asin()

            payload['short_name_product%d' % reward_index] = ' '.join(reward.item_name.split()[:4])

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)


@staff_member_required
def enrollments_purchases_json(request): # pylint: disable=unused-argument, too-many-branches, too-many-statements
    payload = {}

    identifier = request.GET.get('webmunk_id', '')

    enrollment = Enrollment.objects.filter(assigned_identifier=identifier).first()

    if enrollment is not None:
        reward_index = 1

        start = enrollment.enrolled.date()
        end = start + datetime.timedelta(days=(7 * 7))

        # query = enrollment.purchases.filter(purchase_date__gte=start, purchase_date__lte=end).exclude(item_type=None).exclude(item_type='null').exclude(item_type='not-found').exclude(item_type='invalid')
        query = enrollment.purchases.filter(purchase_date__gte=start, purchase_date__lte=end)

        ignore_categories = (
            'vibrator',
            'bedroom',
            'condom',
            'male_toys',
            'lubricant',
            'anal',
            'butt',
            'plug',
            'dildo',
            'massager',
            'incontinence protector',
            'medication',
            'abis book',
            'abis book',
            'gift card',
            'downloadable video game',
            'electronic gift card',
            'abis gift card',
            'financial instruments, products, contracts and agreements',
            'books >',
            'movies & tv  >',
        )

        for category in ignore_categories:
            query = query.exclude(item_type__icontains=category)

        ignore_titles = (
            'coffin',
            'casket',
            'vibrator',
            'bedroom',
            'condom',
            'male toys',
            'lubricant',
            'anal',
            'butt',
            'plug',
            'dildo',
            'massager',
            'incontinence protector',
            'medication',
            'abis book',
            'gift card',
            ' sex ',
            'fuck',
        )

        for keyword in ignore_titles:
            query = query.exclude(item_name__icontains=keyword)

        seen = []

        reward_index = 1

        for purchase in query.order_by('?'):
            if reward_index == 4:
                break

            if (purchase.item_url in seen) is False:
                payload['full_name_product%d' % reward_index] = purchase.item_name

                payload['asin_product%d' % reward_index] = purchase.asin()

                payload['short_name_product%d' % reward_index] = ' '.join(purchase.item_name.split()[:4])

                payload['purchase_date%d' % reward_index] = purchase.purchase_date.isoformat()
                payload['item_type%d' % reward_index] = purchase.item_type

                reward_index += 1

                seen.append(purchase.item_url)

    return HttpResponse(json.dumps(payload, indent=2), content_type='application/json', status=200)

@staff_member_required
def create_asin_lookup(request):
    context = {}

    if request.method == 'POST':
        asins = request.POST.get('asins', '').strip().splitlines()

        job_def = {
              "data_sources": [
                "asin-fetch"
              ],
              "data_types": [
                "enrollment.asin_lookup"
              ],
              "custom_parameters": {
                "asins": asins
              }
        }

        requester = request.user

        print('POST: %s' % request.POST)

        if request.POST.get('upload_to_bucket', '').lower() == 'on':
            requester = get_user_model().objects.filter(username='s3-asin-files').first()

        report_job = ReportJob.objects.create(requester=requester, requested=timezone.now(), job_index=1, job_count=1, parameters=json.dumps(job_def, indent=2))

        context['message'] = 'Request for %s ASIN lookups submitted successfully.' % len(asins)

    return render(request, 'webmunk_asin_lookup.html', context=context)

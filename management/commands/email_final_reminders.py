# pylint: disable=no-member,line-too-long

from __future__ import print_function

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand
from django.template.loader import render_to_string
from django.urls import reverse

from ...models import Enrollment

class Command(BaseCommand):
    help = 'Sends reminders to participants with outstanding tasks.'

    def add_arguments(self, parser):
        pass

    def handle(self, *args, **options): # pylint: disable=too-many-locals
        study_ids = [
            '77480295',
            '88369711',
            '49127118',
            '83113633',
            '74395281',
            '87478725',
            '86203674',
            '66883379',
            '95210396',
            '55481463',
            '61551336',
            '59220935',
            '35368219',
            '39952161',
            '51678443',
            '21430891',
            '18249288',
            '10522008',
            '16503053',
            '50081554',
            '80507686',
            '81508224',
            '64161029',
            '79431129',
            '69655669',
            '41106464',
            '19711214',
            '33003133',
            '30575615',
            '13421382',
            '41132496',
            '50101299',
            '16134983',
            '56840818',
            '21002922',
            '61533263',
            '27618884',
            '11788883',
            '15452444',
            '80752780',
            '75162288',
            '71610470',
            '30458798',
            '21092109',
            '16781756',
            '52911466',
            '73525291',
            '84215463',
            '72054633',
            '30039708',
            '93412117',
            '12790698',
            '30613286',
            '80279567',
            '25276846',
            '73463777',
            '34135872',
            '16938820',
            '77360466',
            '72765263',
            '71114295',
            '57499381',
            '92331535',
            '64599424',
            '39755662',
            '92282485',
            '95879618',
            '24408854',
            '24926333',
            '55191306',
            '24849328',
            '78020072',
            '43669022',
            '18601930',
            '75561324',
            '82719156',
            '96842651',
            '42621877',
            '66879850',
        ]

        for study_id in study_ids:
            enrollment = Enrollment.objects.get(assigned_identifier=study_id)

            has_final_amazon = False
            has_final_survey = False
            did_final_amazon = False
            did_final_survey = False

            for task in enrollment.tasks.all():
                if task.slug == 'amazon-fetch-final':
                    has_final_amazon = True
                    if task.completed is not None:
                        did_final_amazon = True

                if task.slug == 'main-survey-final':
                    has_final_survey = True
                    if task.completed is not None:
                        did_final_survey = True

            if False in [has_final_amazon, has_final_survey, did_final_amazon, did_final_survey]:
#                 if has_final_amazon is False:
#                     print('%s\tamazon-fetch-final missing' % enrollment.assigned_identifier)
#                 elif did_final_amazon is False:
#                     print('%s\tamazon-fetch-final incomplete' % enrollment.assigned_identifier)
#                 elif did_final_amazon:
#                     if has_final_survey is False:
#                         print('%s\tmain-survey-final missing' % enrollment.assigned_identifier)
#                     elif did_final_survey is False:
#                         print('%s\tmain-survey-final incomplete' % enrollment.assigned_identifier)
#                     else:
#                         print('%s\tmain-survey-final unknown' % enrollment.assigned_identifier)
#                 else:
#                     print('%s\tamazon-fetch-final unknown' % enrollment.assigned_identifier)

                raw_identifier = enrollment.current_raw_identifier()

                context = {
                    'identifier': enrollment.assigned_identifier,
                    'tasks': [],
                    'unsubscribe': '%s%s' % (settings.SITE_URL, reverse('unsubscribe_reminders', args=[enrollment.assigned_identifier]))
                }

                request_email_subject = render_to_string('reminders/email_final_reminder_subject.txt', context=context)
                request_email_txt = render_to_string('reminders/email_final_reminder_body.txt', context=context)

                print('SEND to %s' % raw_identifier)

                request_email_html = render_to_string('reminders/email_final_reminder_body.html', context=context)

                message = EmailMultiAlternatives(request_email_subject, request_email_txt, settings.AUTOMATED_EMAIL_FROM_ADDRESS, [raw_identifier])
                message.attach_alternative(request_email_html, 'text/html')
                message.send()


            else:
                print('%s\tOK' % enrollment.assigned_identifier)

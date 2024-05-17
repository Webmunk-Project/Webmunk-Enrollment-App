# -*- coding: utf-8 -*-
# pylint: disable=no-member,line-too-long

from django.core.management.base import BaseCommand

from quicksilver.decorators import handle_lock, handle_schedule, add_qs_arguments

from ...models import ScheduledTask

class Command(BaseCommand):
    help = 'Checks outstanding tasks for completion'

    @add_qs_arguments
    def add_arguments(self, parser):
        parser.add_argument('file', type=str)

    @handle_lock
    @handle_schedule
    def handle(self, *args, **options):
        with open(options.get('file', None), mode='r', encoding='utf-8') as input:
            for line in input:
                if line.startswith('ASIN') is False:
                    tokens = line.split('\t')

                    print('TOKENS: %s' % tokens)

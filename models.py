# pylint: disable=line-too-long, no-member, too-few-public-methods, attribute-defined-outside-init

import base64
import datetime
import json
import logging
import random
import traceback

from urllib.parse import urlparse

import arrow
import keepa
import numpy
import pandas
import pytz

from nacl.secret import SecretBox
from six import python_2_unicode_compatible

from django.conf import settings
from django.contrib.gis.db import models
from django.db import IntegrityError
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.encoding import smart_str

def decrypt_value(stored_text):
    try:
        key = base64.b64decode(settings.ENROLLMENT_SECRET_KEY) # getpass.getpass('Enter secret backup key: ')

        box = SecretBox(key)

        ciphertext = base64.b64decode(stored_text.replace('secret:', '', 1))

        cleartext = box.decrypt(ciphertext)

        return smart_str(cleartext)

    except AttributeError:
        pass

    return None

def encrypt_value(cleartext):
    try:
        key = base64.b64decode(settings.ENROLLMENT_SECRET_KEY) # getpass.getpass('Enter secret backup key: ')

        box = SecretBox(key)

        uft8_bytes = cleartext.encode('utf-8')

        ciphertext = box.encrypt(uft8_bytes)

        return 'secret:' + smart_str(base64.b64encode(ciphertext))

    except AttributeError:
        pass

    return None

def generate_unique_identifier():
    identifier = None

    while identifier is None:
        try:
            identifier = settings.ENROLLMENT_GENERATE_IDENTIFIER()
        except AttributeError:
            identifier = str(random.randint(10000000, 99999999)) # nosec

            identifier = identifier.zfill(8)

        if Enrollment.objects.filter(assigned_identifier=identifier).count() > 0:
            identifier = None

    return identifier

class NumpyEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, numpy.ndarray):
            return o.tolist()

        if isinstance(o, datetime.datetime):
            return o.isoformat()

        if isinstance(o, pandas.DataFrame):
            json_str = o.to_json()

            return json.loads(json_str)

        return json.JSONEncoder.default(self, o)


@python_2_unicode_compatible
class ExtensionRuleSet(models.Model):
    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=1024)
    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)

    rule_json = models.TextField(max_length=(16 * 1024 * 1024), default='[]')

    def __str__(self):
        return str(self.name)

    def rules(self):
        return json.loads(self.rule_json)

@python_2_unicode_compatible
class ArchivedExtensionRuleSet(models.Model):
    class Meta:
        ordering = ['-active_until']

    rule_set = models.ForeignKey(ExtensionRuleSet, related_name='previous_versions', on_delete=models.CASCADE)

    rule_json = models.TextField(max_length=(16 * 1024 * 1024), default='[]')

    active_until = models.DateTimeField()

    def __str__(self):
        return '%s (%s)' % (self.rule_set, self.active_until)

@receiver(pre_save, sender=ExtensionRuleSet)
def archive_rule_set(sender, instance, **kwargs): # pylint: disable=unused-argument
    original_version = ExtensionRuleSet.objects.filter(id=instance.id).first()

    if original_version is not None and original_version.rule_json != instance.rule_json:
        ArchivedExtensionRuleSet.objects.create(rule_set=instance, rule_json=original_version.rule_json, active_until=timezone.now())

@python_2_unicode_compatible
class EnrollmentGroup(models.Model):
    class Meta:
        ordering = ['name']

    name = models.CharField(max_length=(4 * 1024))

    def __str__(self):
        return str(self.name)


@python_2_unicode_compatible
class Enrollment(models.Model):
    class Meta:
        ordering = ['assigned_identifier']

    assigned_identifier = models.CharField(max_length=(4 * 1024), default='changeme', verbose_name='Identifier')
    raw_identifier = models.CharField(max_length=(4 * 1024), default='changeme')

    group = models.ForeignKey(EnrollmentGroup, null=True, blank=True, related_name='members', on_delete=models.SET_NULL)

    enrolled = models.DateTimeField()
    last_fetched = models.DateTimeField()
    last_uninstalled = models.DateTimeField(null=True, blank=True)

    rule_set = models.ForeignKey(ExtensionRuleSet, related_name='enrollments', null=True, blank=True, on_delete=models.SET_NULL)

    contact_after = models.DateTimeField(null=True, blank=True)

    metadata = models.TextField(max_length=(16 * 1024 * 1024), default='{}')

    def latest_data_point(self):
        metadata = json.loads(self.metadata)

        latest = metadata.get('latest_data_point', None)

        if latest is not None:
            here_tz = pytz.timezone(settings.TIME_ZONE)

            return arrow.get(latest).datetime.astimezone(here_tz)

        return None

    def latest_server(self):
        metadata = json.loads(self.metadata)

        server = metadata.get('data_point_server', None)

        if server is not None:
            parsed = urlparse(server)

            return parsed.hostname.split('.')[0]

        return None

    def __str__(self):
        return str(self.assigned_identifier)

    def issues(self):
        open_task_urls = []

        issues = []

        now = timezone.now()

        for task in self.tasks.filter(active__lte=now, completed=None):
            if task.url in open_task_urls and ('identical-tasks' in issues) is False:
                issues.append('identical-tasks')
            else:
                open_task_urls.append(task.url)

        if len(issues) == 0:
            return None

        issue_descriptions = []

        if 'identical-tasks' in issues:
            issue_descriptions.append('identical active tasks')

        return ';'.join(issue_descriptions)

    def assign_random_identifier(self, raw_identifier):
        if raw_identifier == self.current_raw_identifier():
            return # Same as current - don't add

        if hasattr(settings, 'ENROLLMENT_SECRET_KEY'):
            encrypted_identifier = encrypt_value(raw_identifier)

            self.raw_identifier = encrypted_identifier
        else:
            self.raw_identifier = raw_identifier

        if self.assigned_identifier == 'changeme' or self.assigned_identifier is None:
            self.assigned_identifier = generate_unique_identifier()

        self.save()

    def current_raw_identifier(self):
        if self.raw_identifier is not None and self.raw_identifier.startswith('secret:'):
            return decrypt_value(self.raw_identifier)

        return self.raw_identifier

    def fetch_metadata(self):
        return json.loads(self.metadata)


@python_2_unicode_compatible
class ScheduledTask(models.Model):
    enrollment = models.ForeignKey(Enrollment, related_name='tasks', on_delete=models.CASCADE)

    active = models.DateTimeField()

    task = models.CharField(max_length=1024)
    slug = models.SlugField(max_length=1024)
    url = models.URLField(max_length=1024)

    last_check = models.DateTimeField(null=True, blank=True)
    completed = models.DateTimeField(null=True, blank=True)

    metadata = models.TextField(max_length=(16 * 1024 * 1024), default='{}')

    def __str__(self):
        return '%s (%s)' % (self.task, self.slug)

    def fetch_metadata(self):
        return json.loads(self.metadata)

    def is_complete(self):
        now = timezone.now()

        if self.active > now:
            return False

        if self.completed is not None:
            return True

        self.last_check = now
        self.save()

        try:
            if settings.WEBMUNK_CHECK_TASK_COMPLETE(self):
                if self.completed is None:
                    self.completed = now

                self.save()

                return True
        except AttributeError:
            pass

        return False

@receiver(pre_save, sender=ScheduledTask)
def throw_error_if_duplicate(sender, instance, **kwargs): # pylint: disable=unused-argument
    enrollment = Enrollment.objects.get(id=instance.enrollment.id)

    if instance.id is None and enrollment.tasks.filter(slug=instance.slug):
        raise IntegrityError('ScheduledTask with slug "%s" already exists for Enrollment "%s".' % (instance.slug, instance.enrollment))

@python_2_unicode_compatible
class PageContent(models.Model):
    url = models.URLField(max_length=1024)

    retrieved = models.DateTimeField()

    content = models.TextField(null=True, blank=True, max_length=(64 * 1024 * 1024))

    def __str__(self):
        return '%s (%s)' % (self.url, self.retrieved)

    def content_length(self):
        if self.content is not None:
            return len(self.content)

        return None

@python_2_unicode_compatible
class RuleMatchCount(models.Model):
    url = models.URLField(max_length=1024)
    pattern = models.CharField(max_length=1024)
    matches = models.IntegerField()

    checked = models.DateTimeField()

    page_content = models.ForeignKey(PageContent, null=True, blank=True, related_name='rule_matches', on_delete=models.CASCADE)

    def __str__(self):
        return '%s[%s]: %s (%s)' % (self.url, self.pattern, self.matches, self.checked)

    def content_length(self):
        if self.page_content is not None:
            return self.page_content.content_length()

        return None

    def populate_content(self):
        if self.page_content is None:
            check_date = self.checked.replace(microsecond=0, second=0)

            window_start = check_date - datetime.timedelta(seconds=60)
            window_end = check_date + datetime.timedelta(seconds=60)

            matching_page = PageContent.objects.filter(url=self.url, retrieved__gte=window_start, retrieved__lte=window_end).first()

            if matching_page is not None:
                self.page_content = matching_page
                self.save()
            elif self.content is not None:
                self.page_content = PageContent.objects.create(url=self.url, retrieved=check_date, content=self.content)
                self.save()


@python_2_unicode_compatible
class AmazonPurchase(models.Model):
    enrollment = models.ForeignKey(Enrollment, null=True, blank=True, related_name='purchases', on_delete=models.SET_NULL)

    order_url = models.URLField(null=True, blank=True, max_length=4096)

    item_type = models.CharField(max_length=4096, null=True, blank=True)

    item_name = models.CharField(max_length=4096, null=True, blank=True)
    item_url = models.CharField(max_length=4096, null=True, blank=True)

    purchase_date = models.DateField()

    metadata = models.TextField(max_length=(4 * 1024 * 1024), null=True, blank=True)

    def asin(self):
        tokens = self.item_url.split('/')

        for i in range(0, len(tokens)): # pylint: disable=consider-using-enumerate
            if tokens[i] == 'product':
                return tokens[i+1]

        return ''

@python_2_unicode_compatible
class AmazonReward(models.Model):
    participant = models.ForeignKey(Enrollment, null=True, blank=True, related_name='rewards', on_delete=models.SET_NULL)

    wishlist_url = models.URLField(null=True, blank=True)

    item_type = models.CharField(max_length=4096, null=True, blank=True)

    item_name = models.CharField(max_length=4096, null=True, blank=True)
    item_url = models.CharField(max_length=4096, null=True, blank=True)
    item_price = models.FloatField(null=True, blank=True)

    notes = models.TextField(max_length=(1024 * 1024), null=True, blank=True)

    def __str__(self):
        return '%s (%s)' % (self.item_name, self.participant)

    def fetch_asin(self):
        tokens = self.item_url.replace('?', '/').replace('#', '/').split('/')

        for i in range(0, len(tokens)): # pylint: disable=consider-using-enumerate
            if tokens[i] == 'dp':
                return tokens[i + 1]

        return None

@python_2_unicode_compatible
class AmazonASINItem(models.Model):
    asin = models.CharField(max_length=4096, unique=True)

    item_name = models.CharField(max_length=4096, null=True, blank=True)

    keepa_response = models.TextField(max_length=(8 * 1024 * 1024), null=True, blank=True)

    fetched = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '%s (%s)' % (self.item_name, self.asin)

    def fetch_root_category(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            return keepa_data.get('rootCategory', None)

        return None

    def fetch_category(self):
        category = ''

        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            if keepa_data.get('categoryTree', None) is not None:
                for category_item in keepa_data.get('categoryTree', []):
                    if category != '':
                        category = category + ' > '

                    category = category + category_item['name']

        return category

    def fetch_category_ids(self):
        category = ''

        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            if keepa_data.get('categoryTree', None) is not None:
                for category_item in keepa_data.get('categoryTree', []):
                    if category != '':
                        category = category + ' > '

                    category = category + str(category_item['catId'])

        return category


    def fetch_brand(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            brand = keepa_data.get('brand', None)

            return brand

        return None

    def fetch_item_type(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            brand = keepa.get('type', None)

            return brand

        return None

    def fetch_manufacturer(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            brand = keepa_data.get('manufacturer', None)

            return brand

        return None

    def fetch_seller(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            seller_id = keepa_data.get('sellerIds', None)

            if seller_id is None:
                seller_id = keepa_data.get('buyBoxSellerId', None)

            return seller_id

        return None

    def fetch_size(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            return keepa_data.get('size', None)

        return None

    def fetch_title(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            return keepa_data.get('title', None)

        return None

    def fetch_is_on_keepa(self):
        if self.keepa_response is not None:
            keepa_data = {}

            try:
                keepa_data = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_data = json.loads(self.keepa_response)

                self.cached_keepa = keepa_data

            if keepa_data.get('error', None) is None:
                return True

            return False

        return None


    def populate_title(self):
        if self.keepa_response is not None:
            keepa_response = {}

            try:
                keepa_response = self.cached_keepa
            except: # pylint: disable=bare-except
                keepa_response = json.loads(self.keepa_response)

                self.cached_keepa = keepa_response

            if keepa_response.get('title', None) is None:
                manufacturer = keepa_response.get('manufacturer', None)
                brand = keepa_response.get('brand', None)
                size = keepa_response.get('size', None)
                item_type = keepa_response.get('type', None)

                new_title = ''

                if manufacturer is not None:
                    new_title += manufacturer

                if brand is not None:
                    if new_title != '':
                        new_title += ', '

                    new_title += brand

                if size is not None:
                    if new_title != '':
                        new_title += ', '

                    new_title += size

                if item_type is not None:
                    if new_title != '':
                        new_title += ' '

                    new_title += '(%s)' % item_type

                self.item_name = new_title
            else:
                self.item_name = keepa_response['title']

            self.save()

    def populate(self, force=False):
        if force is False and self.keepa_response is not None:
            keepa_response = json.loads(self.keepa_response)

            if keepa_response.get('error', None) is None:
                return

        try:
            api = keepa.Keepa(settings.KEEPA_API_KEY)

            products = api.query(self.asin, progress_bar=False, buybox=True)

            logging.debug('%s: %s', self.asin, json.dumps(products, indent=2, cls=NumpyEncoder))

            product = None

            if len(products) > 0 and products[0] is not None:
                product = products[0]

            if product is not None:
                try:
                    self.keepa_response = json.dumps(product, indent=2, cls=NumpyEncoder)
                except ValueError:
                    pass # Pandas issue
            else:
                raise ValueError('Unable to save Keepa response')
        except Exception as ex: # pylint: disable=broad-exception-caught
            payload = {
                'error': 'Unable to retrieve product - exception encountered.'
            }

            payload['stacktrace'] = ''.join(traceback.TracebackException.from_exception(ex).format())

            self.keepa_response = json.dumps(payload, indent=2, cls=NumpyEncoder)

        self.fetched = timezone.now()
        self.save()

        self.populate_title()

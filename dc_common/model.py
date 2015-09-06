# model.py - Peewee database model

from peewee import *
from config import database, migrator
from enum import Enum
import datetime
import enum34

database.connect()

def atomic():
    ''' To run a bunch of stuff within a transaction; e.g.:

    with model.atomic() as xact:
        foo
        bar
        baz
        if error:
            xact.rollback()

    '''
    return database.atomic()

class BaseModel(Model):
    class Meta:
        database = database

    @staticmethod
    def update_schema(check_update,from_version):
        ''' Implement this to migrate a database from an older version, and return the current version of this table.

        Only process updates if check_update is true. Example:

            if check_update and from_version < 1:
                migrate(
                    migrator.add_column('BlahTable', 'foo', BlahTable.foo),
                    migrator.add_column('BlahTable', 'bar', BlahTable.baz), # changed from 'bar' to 'baz' in verison 2
                )
            if check_update and from_version < 2:
                migrate(
                    migrator.rename_column('BlahTable', 'bar', 'baz'),
                )
            return 2
        '''
        return 0

''' Site-level stuff '''

class Global(BaseModel):
    ''' Settings for the site itself (schema version, generic global config, etc.) '''
    key = CharField(unique=True)
    int_value = IntegerField(null=True)
    string_value = CharField(null=True)

    @staticmethod
    def update_schema(check_update,from_version):
        ''' Hook for migrating schemata, e.g. table names '''
        return 0

class User(BaseModel):
    ''' A user in the system '''
    username = CharField(unique=True)
    display_name = CharField(unique=True)
    homepage = CharField(null=True)
    pwhash = CharField() # We're going to use bcrypt. Right? Right.
    email = CharField()
    is_admin = BooleanField(default=False)
    reset_key = CharField(null=True)

class AdminLog(BaseModel):
    ''' Administrative action log '''
    timestamp = DateTimeField(default=datetime.datetime.now)
    user = ForeignKeyField(User, related_name='actions')
    ip = CharField()
    url = CharField()
    description = TextField()
    session_id = CharField()
    class Meta:
        indexes = (
            (('user', 'timestamp'), False),
        )

class Theme(BaseModel):
    owner = ForeignKeyField(User, related_name='themes')
    name = CharField()
    max_image_width = IntegerField()
    css_file = CharField()

class Series(BaseModel):
    owner = ForeignKeyField(User, related_name='series')
    title = CharField()
    theme = ForeignKeyField(Theme, null=True)

class Story(BaseModel):
    series = ForeignKeyField(Series, related_name='stories')
    title = CharField()
    theme = ForeignKeyField(Theme, null=True)

class Chapter(BaseModel):
    story = ForeignKeyField(Story, related_name='chapters')
    title = CharField()
    recap_text = TextField(null=True)
    theme = ForeignKeyField(Theme, null=True)

class Page(BaseModel):
    series = ForeignKeyField(Series, related_name='pages')
    chapter = ForeignKeyField(Chapter, related_name='pages', null=True)
    title = CharField()
    publish_date = DateTimeField(default=datetime.datetime.now)
    is_visible = BooleanField(default=False)
    notes = TextField(null=True)
    theme = ForeignKeyField(Theme, null=True)

class Asset(BaseModel):
    user = ForeignKeyField(User, related_name='assets')
    content_file = CharField(null=True)
    content_text = TextField(null=True)

class PageContent(BaseModel):
    display_order = IntegerField()
    page = ForeignKeyField(Page, related_name='assets')
    asset = ForeignKeyField(Asset, related_name='pages')

class Transcript(BaseModel):
    page = ForeignKeyField(Page, related_name='transcripts')
    text = TextField()
    accepted = BooleanField(default=False)
    submitter_name = CharField(null=True)
    submitter_email = CharField(null=True)
    submitter_homepage = CharField(null=True)

class BlogEntry(BaseModel):
    user = ForeignKeyField(User, related_name='comments')
    page = ForeignKeyField(Page, related_name='comments', null=True)
    date_posted = DateTimeField(default=datetime.datetime.now, index=True)
    title = CharField()
    text = TextField()
    is_visible = BooleanField(default=False)

''' Table management '''

all_types = [
    Global, #MUST come first
    User,
    AdminLog,
]

def create_tables():
    with database.atomic():
        database.create_tables(all_types, safe=True)
        for table in all_types:
            schemaVersion, created = Global.get_or_create(key='schemaVersion.' + table.__name__)
            schemaVersion.int_value = table.update_schema(not created, schemaVersion.int_value)
            schemaVersion.save()

def drop_all_tables(i_am_really_sure=False):
    ''' Call this if you need to nuke everything and restart. Only for development purposes, hopefully. '''
    if not i_am_really_sure:
        raise "You are not really sure. Call with i_am_really_sure=True to proceed."
    with database.atomic():
        for table in all_types:
            database.drop_table(table)

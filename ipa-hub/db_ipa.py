from google.appengine.ext import db

class DB_IPA(db.Model):
    bundle_id = db.StringProperty()
    version = db.StringProperty()
    name = db.StringProperty()
    blob_info_key = db.StringProperty()
    created_time = db.DateTimeProperty(auto_now_add=True)
    modified_time = db.DateTimeProperty(auto_now=True)

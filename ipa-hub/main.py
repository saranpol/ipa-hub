#!/usr/bin/env python
import webapp2
import os
import urllib
import jinja2
from db_ipa import *
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers

JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)


import cloudstorage as gcs

from google.appengine.api import app_identity
my_default_retry_params = gcs.RetryParams(initial_delay=0.2,
                                          max_delay=5.0,
                                          backoff_factor=2,
                                          max_retry_period=15)
gcs.set_default_retry_params(my_default_retry_params)


def get_bucket_name() :
    return os.environ.get('ipa-hub.appspot.com', app_identity.get_default_gcs_bucket_name())
    
def get_filename(key):
    bucket_name = get_bucket_name()
    bucket = '/' + bucket_name
    filename = bucket + '/ipa/' + key + '.ipa'
    return filename


class MainHandler(webapp2.RequestHandler):
    def get(self):
        upload_url = blobstore.create_upload_url('/upload', gs_bucket_name = get_bucket_name())
        template_values = {'upload_url': upload_url}
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.write(template.render(template_values))

# class Upload(webapp2.RequestHandler):
class Upload(blobstore_handlers.BlobstoreUploadHandler):
    def post(self):
        bundle_id = self.request.get('bundle_id')
        version = self.request.get('version')
        name = self.request.get('name')
        # ipa = self.request.get('ipa')
        
        # if not bundle_id or not version or not name or not ipa :
        if not bundle_id or not version or not name :
            self.response.write('please check input')
            return
        
        k = bundle_id + '_' + version
        e = DB_IPA.get_or_insert(key_name=k)
        e.bundle_id = bundle_id
        e.version = version
        e.name = name
        upload_files = self.get_uploads('ipa')  # 'file' is file upload field in the form
        blob_info = upload_files[0]
        e.blob_info_key = str(blob_info.key())
        e.put()

        # filename = get_filename(k)

        # try:
        #     write_retry_params = gcs.RetryParams(backoff_factor=1.1)
        #     gcs_file = gcs.open(filename,
        #                         'w',
        #                         content_type='application/octet-stream',
        #                         #content_type='image/png',
        #                         retry_params=write_retry_params)
        #     gcs_file.write(ipa)
        #     gcs_file.close()

        # except Exception, e:  # pylint: disable=broad-except
        #     self.response.write('There was an error running!')
        # else:
        #     self.response.write('https://ipa-hub.appspot.com/ipa?key='+k)
        self.response.write('https://ipa-hub.appspot.com/ipa?key='+k)

class ServeHandler(blobstore_handlers.BlobstoreDownloadHandler):
    def get(self, resource):
        resource = str(urllib.unquote(resource))
        blob_info = blobstore.BlobInfo.get(resource)
        self.send_blob(blob_info)

class GetFile(webapp2.RequestHandler):
    def get(self):
        key = self.request.get('key')
        if not key :
            return
        self.response.headers['Content-Type'] = "application/octet-stream"
        filename = get_filename(key)
        gcs_file = gcs.open(filename)
        #self.response.write(gcs_file.readline())
        #gcs_file.seek(-1024, os.SEEK_END)
        #self.response.write(gcs_file.read())
        buf = gcs_file.read()
        while buf:
            self.response.out.write(buf)
            buf = gcs_file.read()
        gcs_file.close()


class Plist(webapp2.RequestHandler):
    def get(self, key):
        if not key :
            return
        e = DB_IPA.get_by_key_name(key)
        template_values = {'name':e.name,
        'bundle_id':e.bundle_id,
        'version':e.version,
        'file_url':'https://ipa-hub.appspot.com/get_file?key='+e.bundle_id+'_'+e.version}
        if (e.blob_info_key) :
            template_values['file_url'] = 'https://ipa-hub.appspot.com/serve/' + e.blob_info_key
        template = JINJA_ENVIRONMENT.get_template('ipa.plist')
        self.response.headers['Content-Type'] = "text/plain"
        self.response.write(template.render(template_values))



class IPA(webapp2.RequestHandler):
    def get(self):
        key = self.request.get('key')
        if not key :
            return
        template_values = {'url':'itms-services://?action=download-manifest&url=https://ipa-hub.appspot.com/plist/'+str(key)}
        #template_values = {'url':'itms-services://?action=download-manifest&url=https://ipa-hub.appspot.com/plist'}
        #template_values = {'url':'itms-services://?action=download-manifest&url=https://dl.dropboxusercontent.com/s/hkpx5bou7eusqe9/gamet'}
        #template_values = {'url':'itms-services://?action=download-manifest&url=https://ipa-hub.appspot.com/images/gamet'}
        template = JINJA_ENVIRONMENT.get_template('ipa.html')
        self.response.write(template.render(template_values))


app = webapp2.WSGIApplication([
    ('/', MainHandler),
    ('/upload', Upload),
    ('/get_file', GetFile),
    ('/plist/(.*)', Plist),
    ('/ipa', IPA),
    ('/serve/([^/]+)?', ServeHandler),
], debug=True)

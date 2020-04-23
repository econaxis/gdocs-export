from __future__ import absolute_import

import json
import pickle
import logging
from collections import defaultdict

from apiclient.discovery import build
from google.auth.transport.requests import AuthorizedSession

# suppress warnings from google api client library
logging.getLogger('googleapiclient.discovery_cache').setLevel(logging.ERROR)

class GoogleDoc():
    """
    Google doc class
    Contains document metadata and revision history
    """
    def __init__(self, file_id, credentials, fetch_metadata=True, **kwargs):
        """
        Create a GoogleDoc instance
        Requires either credentials or keyfile arguments to be specified

        :param file_id: ID string that can be found in the Google Doc URL
        :param credentials: Credentials object
        :param fetch_metadata: Flag indicating whether to fetch additional doc-level metadata, e.g. title
        :param kwargs: Additional kwargs to pass to Document constructor

        :type file_id: str
        :type credentials: google.auth.credentials.Credentials
        :type fetch_metadata: bool
        """
        # google credentials object instance (oauth2client.OAuth2Credentials or subclass)
        self.credentials = credentials
        # file identifier string from the URL
        self.file_id = file_id

        # dictionary of document metadata via Google API
        self.metadata = self._fetch_metadata() if fetch_metadata else None
        """dictionary of document metadata via Google API"""

        # document title
        self.name = self.metadata['name'] if self.metadata else None
        # dict of raw revision metadata, containing keys "changelog" and "chunkedSnapshot"
        self.revisions_raw = self._download_revision_details()

    def _gdrive_api(self):
        """
        Return an authorized drive api service object
        """
        return build('drive', 'v3', credentials=self.credentials)

    def _fetch_metadata(self):
        """
        Fetch a dictionary of document-level metadata via Google API
        """
        return self._gdrive_api().files().get(fileId=self.file_id).execute()

    def _last_revision_id(self):
        """
        Return the id of the last revision to a document, using the offical google api v3
        """
        revision_metainfo = self._gdrive_api().revisions().list(fileId=self.file_id).execute()
        if len(revision_metainfo['revisions']) == 0:
            # detailed metadata endpoint will have a revision corresponding to doc creation
            return 1
        else:
            return revision_metainfo['revisions'][-1]['id']
    
    def _generate_revision_url(self, start, end):
        """
        Generates a url for downloading revision details (using undocumented google api endpoint)
        """
        base_url = 'https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start={start}&end={end}'
        url = base_url.format(file_id=self.file_id, start=start, end=end)
        return url

    def _download_revision_details(self):
        """
        download json-like data with revision info
        """
        last_revision_id = self._last_revision_id()
        url = self._generate_revision_url(start=1, end=last_revision_id)
        response = AuthorizedSession(self.credentials).get(url)
        response.raise_for_status()
        data = json.loads(response.text[5:])
        return data
    def clear(self):
        self.revisions_raw = ""


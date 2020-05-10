from processing.sql import db_connect, reload_engine, scrt, az_upload_dbs, az_download_dbs, get_db_path
from threading import Lock

import logging
logger = logging.getLogger(__name__)


class OwnerManager():
    def __init__(self):
        self.owner_lock = Lock()
        self.owners = {}

    def __call__(self, owner_id):

        with self.owner_lock:
            if owner_id in self.owners:
                logger.warning("Found old owner_id, using")
                return self.owners[owner_id]

        @db_connect
        def create_owner(owner_id=None):
            assert owner_id != None, "owner_id is none"

            reload_engine(owner_id, create_new = True)
            #Debugging, added secret for no unique key constraint
            reload_engine(owner_id).remove()

            fileid_obj_map = {}
            dict_lock = Lock()

            return fileid_obj_map, dict_lock

        with self.owner_lock:
            self.owners[owner_id] = create_owner(owner_id=owner_id)
            return self.owners[owner_id]

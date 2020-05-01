from processing.sql import db_connect, v_scoped_session, scrt
from threading import Lock
from processing.models import Owner
from datetime import datetime

import logging
logger = logging.getLogger(__name__)



class OwnerManager():

    def __init__(self):
        self.owner_lock = Lock()
        self.owners = {}

    def __call__(self, userid):

        with self.owner_lock:
            if userid in self.owners:
                logger.warning("Found old userid, using")
                return self.owners[userid]

        @db_connect
        def create_owner(userid):
            sess = v_scoped_session()
            #Debugging, added secret for no unique key constraint
            temp = userid[0:45] + datetime.now().strftime("%m-%d-%H-%f") + scrt
            owner = Owner(name=temp[0:49])

            sess.add(owner)
            sess.commit()

            owner_id = owner.id
            v_scoped_session.remove()

            fileid_obj_map = {}
            dict_lock = Lock()
            return owner_id, fileid_obj_map, dict_lock

        with self.owner_lock:
            print("creating new user: %s", userid)
            logger.warning(self.owners)
            self.owners[userid] = create_owner(userid)
            return self.owners[userid]



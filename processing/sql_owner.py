
from threading import Lock
from processing.models import Owner
from datetime import datetime



class OwnerManager():
    def __init__(self):
        self.owners = {}

    def __call__(self, userid):
        if userid in self.owners:
            return self.owners[userid]

        from processing.sql import db_connect, v_scoped_session, scrt


        @db_connect
        def create_owner(userid):
            sess = v_scoped_session()
            #Debugging, added secret for no unique key constraint
            temp = userid[0:45] + datetime.now().strftime("%m-%d-%h-%f") + scrt
            owner = Owner(name=temp[0:49])

            sess.add(owner)
            sess.commit()
            sess.close()
            v_scoped_session.remove()

            fileid_obj_map = {}
            dict_lock = Lock()
            return owner, fileid_obj_map, dict_lock

        self.owners[userid] = create_owner(userid)

        return self.owners[userid]



import uuid

class Config:
    def __init__(self, workingPath = None, homePath = None, creds = None, userid = None):
        self.userid = userid
        self.creds = creds
    def set_creds(self, creds):
        self.creds = creds
    def generate_id(self):
        #Deprecated
        return
        self.userid = str(uuid.uuid4())
        self.workingPath = self.homePath + "data/" + self.userid + "/"
        return self.userid
    def get_flask_config(self):
        return dict(SECRET_KEY = str(uuid.uuid4())

from flaskr.get_files import loadFiles
import pickle

if __name__ == "__main__":
    uid = "527e4afc-4598-400f-8536-afa5324f0ba4"
    fileid = 'root'
    homePath =  "/home/henry/pydocs/"
    workingPath =  homePath + 'data/' + uid + '/'
    creds = pickle.load(open(workingPath + 'creds.pickle', 'rb'))
    loadFiles(uid, workingPath, fileid, creds)

import requests
import pickle
import os
import json
import random
import re

if not os.path.exists('/tmp/words_dictionary.pickle'):
    wordlist = requests.get("https://raw.githubusercontent.com/dwyl/english-words/master/words_dictionary.json").json()
    wordlength = [[] for i in range(50)]

    for words in wordlist:
        wordlength[len(words)].append(words)
    pickle.dump(wordlength, open('/tmp/words_dictionary.pickle', 'wb'))
else:
    wordlength = pickle.load(open('/tmp/words_dictionary.pickle', 'rb'))

p = "obfuscated.json"

d = json.load(open(p, 'r'))

for text in d:
    #pre parse
    t = text["content"]


    splitidx = [x.start() for x in re.finditer(" |\n|,|\.", t)]
    tlist = list(t)

    for i in range(len(splitidx)-1):
        start = splitidx[i] + 1
        end = splitidx[i+1]
        length = end-start

        if not wordlength[length]:
            # No words exist at this length
            continue
        newword = random.choice(wordlength[length])
        tlist[start:end] = newword
    text["content"] = ''.join(tlist)

json.dump(d, open('obfuscated.json', 'w'))


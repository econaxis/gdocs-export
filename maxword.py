from __future__ import print_function
import pickle
import tkinter
from load import append_df_to_excel
import math
from collections import OrderedDict
from pprint import PrettyPrinter
from datetime import datetime, timezone
import numpy
import matplotlib.pyplot as plt
import requests
import os.path
import pandas as pd
from pathlib import Path

pp = PrettyPrinter(indent=3)
EXCEL_PATH = 'text.xlsx'
BINS = 400

def main():
	csvdata = pd.read_excel(EXCEL_PATH).drop("Unnamed: 0",1).set_index("index")
	cols = list(csvdata.columns)
	dates = list(csvdata.index)
	minDate = dates[0].to_pydatetime()
	maxDate= dates[-1].to_pydatetime()


	increment = (maxDate-minDate)/BINS
	timeBuckets = [i*increment+minDate for i in list(range(BINS+1))]

	dates_map ={}
	currentInd = 1
	for d in dates:
		if(d>=timeBuckets[currentInd]):
			#Move on to next bucket
			while(d>timeBuckets[currentInd]):
				currentInd+=1
			dates_map[d] = currentInd
		else:
			dates_map[d] = currentInd-1


	maxWords = pd.DataFrame(index = timeBuckets, columns = cols[1:])
	maxWords.loc["Highest Word Count"] = 0


	timeMapIndex = 0
	processed = []



	for (index, f) in enumerate(cols):
		#Iterate through files
		prevMap = [dates_map[dates[0]], 0]


		print("D: %d  out of %d"%(index, len(cols)))

		trimmedDates = list(csvdata[f].dropna().index)
		trimmedDates.append(dates[-1])

		for (dat_ind, d) in enumerate(trimmedDates):
			#Iterate through dates(long)
			prevMap[1] = max(prevMap[1], csvdata.loc[d,f])
			if(dates_map[d]>prevMap[0]):
				#If new bucket is reached, then enter max word into cell 
			
				maxWords.loc[timeBuckets[prevMap[0]],f] = prevMap[1]
				prevD = prevMap[0]
				curD = dates_map[d]
				maxWords.loc["Highest Word Count", f] = max(
					maxWords.loc["Highest Word Count", f], prevMap[1])


			#	Function for filling in cells between
				for betweenCells in timeBuckets[prevD:curD]:
					maxWords.loc[betweenCells,f] = prevMap[1]					


				#Reset prevMap
				prevMap[0] = dates_map[d]



	pickle.dump(maxWords, open('maxwords.pickle', 'wb'))
	pp.pprint(maxWords)

	with open('maxwords.pickle', 'wb') as mw:
		pickle.dump(maxWords, mw)
	append_df_to_excel('text.xlsx',maxWords, sheet_name = "maxWords", truncate_sheet=True)


def mwHighlighter(x):
	#Applies styling to dataframe maxWords

	df = x.copy()



if __name__ == "__main__":
	main()
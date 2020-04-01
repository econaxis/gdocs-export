from __future__ import print_function
import pickle
import tkinter
from load import append_df_to_excel
import math
from collections import OrderedDict
from pprint import PrettyPrinter
import seaborn as sns
from datetime import datetime, timezone
import bisect
import numpy
import matplotlib.pyplot as plt
import requests
import os.path
import pandas as pd
from pathlib import Path

DBG_LIMIT = 200

pp = PrettyPrinter(indent=3)
EXCEL_PATH = 'text.xlsx'
BINS = 400

def main():
	#csvdata = pd.read_excel(EXCEL_PATH).set_index("Unnamed: 0")

	csvdata = pickle.load(open('csvdata_df.pickle', 'rb')).drop("Last Mod", axis = 0)


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
			while(d>timeBuckets[currentInd] and currentInd +1< len(timeBuckets)):
				currentInd+=1
			dates_map[d] = currentInd
		else:
			dates_map[d] = currentInd-1


	maxWords = pd.DataFrame(index = timeBuckets, columns = cols[1:])
	maxWords.loc["Highest Word Count"] = 0


	timeMapIndex = 0
	processed = []



	for (index, f) in enumerate(cols[:DBG_LIMIT]):
		#Iterate through files
		prevMap = [dates_map[dates[0]], -1, -1]
		processed.append(f)

		print("D: %d  out of %d"%(index, len(cols)))

		trimmedDates = list(csvdata[f].dropna().index)
		trimmedDates.append(dates[-1])

		for (dat_ind, d) in enumerate(trimmedDates):
			#Iterate through dates(long)
			changedInIter = False


			#DOWNLOAD mode
			'''
			if(csvdata.loc[d, f]>prevMap[1]):
				prevMap[1] = csvdata.loc[d, f]
				changedInIter = True
			'''

			#NO DOWNLOAD MODE

			prevMap[1]+=csvdata.loc[d, f]
			changedInIter = True
			
			if(dates_map[d]>prevMap[0]):
				#If new bucket is reached, then enter max word into cell 


				if (changedInIter == False and dat_ind>0):
					prevMap[1] = csvdata.loc[trimmedDates[dat_ind-1], f]


				maxWords.loc[timeBuckets[prevMap[0]],f] = prevMap[1]
				prevD = prevMap[0]
				curD = dates_map[d]

				if(maxWords.loc["Highest Word Count", f] < prevMap[1]
					or math.isnan(maxWords.loc["Highest Word Count", f])):
					
					maxWords.loc["Highest Word Count", f] = prevMap[1]
				

			#	Function for filling in cells between
			#	for betweenCells in timeBuckets[prevD:curD]:
			#		maxWords.loc[betweenCells,f] = prevMap[1]					


				#Reset prevMap
				prevMap[0] = dates_map[d]
				prevMap[2] = prevMap[1]
				prevMap[1] = 0
				#if(d == dates[-1]):
					#Last date reached, special case
					#maxWords.loc[timeBuckets[prevMap[0]], f] =csvdata.loc[trimmedDates[dat_ind-1], f]


	pp.pprint(maxWords)
	maxWords = maxWords.iloc[:, 0:DBG_LIMIT]



	csvdata.loc["Highest Word Count"] = maxWords.loc["Highest Word Count"]





	#open('style.html', 'w').write(applyStyles(maxWords).render())


	pickle.dump(maxWords, open('maxwords.pickle', 'wb'))

	#open('csvdata.html', 'w').write(applyStyles(csvdata).render())

#	pickle.dump(maxWords, open('maxwords.pickle', 'wb'))
#	pp.pprint(maxWords)


#	with open('maxwords.pickle', 'wb') as mw:
#		pickle.dump(maxWords, mw)
	

	#append_df_to_excel('text.xlsx',maxWords, sheet_name = "maxWords", truncate_sheet=True)

#	pd.set_option('display.max_colwidth', 10)
#	maxWords.to_html('i.html')


def applyStyles(df):
	idx = pd.IndexSlice
	subset = df.index.difference(["Highest Word Count"])
	dfStyler = df.style \
	.apply(mwHighlighter, axis=0, subset = idx[subset, :])

	dfStyler = dfStyler \
	.apply(mwHighlighter,axis = 1,subset=idx["Highest Word Count", :])\
 	.set_precision(0)\
	.set_table_styles([{
		'selector': 'table, th, td',
		'props': [
			#("table-layout", "fixed"),
			("border-collapse", "collapse"),
			("overflow", "hidden"),
			("max-width", "3px"),
		#	("max-height", "4px"),
			("font-size", "3px")
		]
	}])

	return dfStyler



def mwHighlighter(x):
	#Applies styling to dataframe maxWords
	numColors = 300


	#Create colormap to only retain medial values
	MED_VALUE = 50
	cm = sns.color_palette("Blues", numColors+2*MED_VALUE+1).as_hex()
	del cm[:MED_VALUE]
	del cm[-MED_VALUE:]

	
	st = x.copy()
	st[:] = ""
	words = sorted(list(x.dropna()))
	i0 = bisect.bisect_right(words, 0)
	del words[:i0]

	if(len(words)==0):
		#Empty list after preprocessing
		st[:] = 'color: black; opacity: 0.1'
		return st

	minW = max(words[0],1)

	#For reasonble colors
	maxW = int(max(words[-1], 1)) 
	#print("%d %d"%(minW, maxW))
	diff = maxW - minW
	#pp.pprint("%d %d %d"%(minW, diff, maxW))

	sameColorMode = False
	if(diff == 0):
		sameColorMode = True


	for (index,val) in enumerate(x):
		if(math.isnan(val) or val==0):
			st[index] = 'color: black;opacity: 0.1'
			continue

		if(sameColorMode):
			st[index] = 'background-color: '+ cm[numColors-1]
			continue
		cmapIndex = min(int((val-minW)/diff * numColors), numColors-1)
		
		st[index] = 'background-color: ' + cm[cmapIndex]
	
	#pp.pprint(st)
	return st

if __name__ == "__main__":
	main()
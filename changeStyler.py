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


	


if __name__ == "__main__":
	main()
# Export all Google Docs Revisions as a CSV File

Google Docs stores all revisions made to a document since the beginning. There's no official way to export all these revisions using either the GUI or using the official Google Drive API. You can only view some revisions by clicking on "See changes" in the Docs UI. Still, we can't export these revisions. However, there is an undocumented API endpoint (that I discovered from seeing Draftback) that has all the edits stored by Google Docs. This contains all the edits made (up to single keystroke resolution).


You can access this data (as an unformatted JSON file) by going to:
```
https://docs.google.com/document/d/{file_id}/revisions/load?id={file_id}&start=1&end={end}
```
 - {file_id} : ID of the Google Docs file
 - {end} : end revision number.

## Finding the ID

 A Google Docs link looks like this: 
 ```
https://docs.google.com/document/d/1b6qJW2miNoYpSAbg/edit
```

The file ID would be anything between the "/d/" and "/edit". In this case, the ID would be "1b6qJW2miNoYpSAbg".

## Finding the end revision number

End revision number tells the API from what range (start to end) to load the revisions. Entering an end revision number greater than the number of revisions a document has will result in an error and nothing being downloaded. Unfortunately, it's hard to find the number of revisions a document has without calling an API.

The easiest way is to test numbers at increasing intervals. Ideally, we'd want to extract the longest range of revisions (from document creation to the present time), so test end revision numbers in increasing intervals 50, 100, 500, 1000, 2000, 3000, 5000 until there's an error ("Sorry, unable to open the file at present.  Please check the address and try again.").

This means we've reached the revision limit for that particular document. Decrease the end revision number until you a file download ("json.txt" file)

This "json.txt" file contains all the revision history of a Google Docs.


# Usage

Follow the steps above to get the json.txt

1. Clone the repository
2. Move the json.txt file into the root of the repository
3. Install pip requirements `pip install -r requirements.txt`
4. Run `python get_files.py json.txt`
5. There should be a operations.csv containing the document text at every single revision captured.

There's another way to export revisions of a document without the guessing-and-checking of end revision ID. (todo).

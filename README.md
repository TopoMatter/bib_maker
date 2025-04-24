# aps_bib_maker
A simple python script that constructs a bib file from a list of DOIs.

Usage: python3 bib_maker.py [options] input_file output_file.bib

Construct a bib file out of the data stored in the input file. 

Types of input files:

1) Each row of the input file contains either a DOI, or it contains the 
desired label for the bib entry followed by a DOI.

2) The input file is a bbl file. Then the code will attempt to read it, 
extract all labels and DOIs, and use them to generate the output bib file. 
This is an attempt to `clean' existing bbl files, and it will fail if the
code doesen't manage to find the DOIs.

Options:

  -o, --overwrite  Overwrite the output file.
  
  -h, --help       Print this message and exit.

Note:
  - This has been written using pybtex version 0.24.0
  - If you find that some journal abbreviations are missing, please help me
    complete the list.


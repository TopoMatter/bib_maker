# bib_maker
A simple python script that constructs a bib file from a list of DOIs.

**Please bear in mind that this script is experimental, you might encounter bugs.**

Usage: ```python3 bib_maker.py [options] input_file output_file.bib```

Types of input files:

1) Each row of the input file contains either a DOI, or it contains the 
desired label for the bib entry followed by a DOI.

2) The input file is a bbl file. Then the code will attempt to read it, 
extract all labels and DOIs, and use them to generate the output bib file. 
This is an attempt to `clean' existing bbl files.

For more information: ```python3 bib.maker.py --help```

Note:
  - This has been written using pybtex version 0.24.0
  - The `experimental' setting uses the terminal-based browser called lynx
  - The current version is in testing, and so it has ```DEBUG_MODE = True```
  - If you find that some journal abbreviations are missing, please help me
    complete the list.


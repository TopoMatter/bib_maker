import pandas
import sys
import subprocess
import getopt
import pybtex
import string
from pybtex.database import parse_file, BibliographyData, Entry

alphabet = string.ascii_lowercase

def usage():
    print( """\
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

"""
)

BIB_FILE = None
INPUT_FILE = None
OVERWRITE = False

def rtfm(s):
    print( "bib_maker:", s)
    print( "Try 'bib_maker --help' for more information.")
    sys.exit(1)


def parse_args():
    global BIB_FILE, INPUT_FILE, OVERWRITE

    try:
        opts, remaining_args = \
            getopt.getopt(sys.argv[1:],
                          "oh",
                          ["overwrite", "help",])
    except getopt.GetoptError:
        rtfm("unrecognized option")

    try:
        INPUT_FILE = remaining_args[0]
        BIB_FILE = remaining_args[1]
    except:
        rtfm("missing in/out file")

    if INPUT_FILE[-4:] == '.bbl':
        extract_input_from_bbl(INPUT_FILE)
        INPUT_FILE = 'temp_input_from_bbl.txt'

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-o", "--overwrite"):
            OVERWRITE = True


def abbreviate_journal_names(bibfile):
    """ From Anton.
    """
    bib = parse_file(bibfile)

    # updated version of the file found at:
    # https://abbrv.jabref.org/journals/journal_abbreviations_geology_physics.csv
    abbreviations = pandas.read_csv(
        "journal_abbreviations.csv",
        on_bad_lines="skip",
        sep=',',
        names=["abbr", "o1", "o2"],
    )

    for item in bib.entries.values():
        if "journal" not in item.fields:
            continue

        found_abbreviation = False
        for ind in abbreviations.index:
            if item.fields["journal"].lower() == \
               abbreviations.abbr.values[ind].lower():
                item.fields["journal"] = abbreviations.o1.values[ind]

                found_abbreviation = True

        # ignore arXiv when listing not found abbreviations
        if item.fields["journal"].lower().find('arxiv') > -1:
            found_abbreviation = True 

        if not found_abbreviation:
            print(f"{item.fields['journal']} not in list")

    bib.to_file(bibfile)


def extract_input_from_bbl(bblfilename, 
                           outfilename='temp_input_from_bbl.txt'):
    """
    """
    infile = open(bblfilename, 'r')

    all_labels = []
    all_DOIs = []

    # put everything into one row
    fulltext = ''
    for myline in infile.readlines():
        fulltext += myline


    infile.close()

    finished = False
    while not finished:

        if fulltext.find("\\bibitem") == -1: # no more entries
            finished = True
            continue

        fulltext = fulltext[fulltext.find("\\bibitem"):]
        fulltext = fulltext[fulltext.find("]")+2:]

        label = fulltext[:fulltext.find("}")].strip()

        if len(label) < 1 or label.find("\\") > -1: # still in preamble
            continue

        all_labels.append(label)

        fulltext = fulltext[fulltext.find("\\BibitemOpen"):]

        bibitem = fulltext[:fulltext.find("\\BibitemShut")]

        DOI = 'DOI_NOT_FOUND'

        # check if DOI is explicitly listed
        if bibitem.find("\\doibase") > -1:
            bibitem = bibitem[bibitem.find("\\doibase")+8:]
            DOI = bibitem[:bibitem.find("}")].strip()

        # maybe there's a hyperlink that contains the DOI?
        elif bibitem.find("\\href") > -1:
            ind_start = bibitem.find("/10.")
            if ind_start > -1 and bibitem[ind_start+8] == "/":
                bibitem = bibitem[ind_start+1:]
                DOI = bibitem[:bibitem.find("}")].strip()
                # trim extra bits after the DOI in the url
                if DOI.rfind("&") > -1:
                    DOI = DOI[:DOI.rfind("&")]
                if DOI.rfind("?") > -1:
                    DOI = DOI[:DOI.rfind("?")]

        all_DOIs.append(DOI)


    outfile = open(outfilename, 'w')
    for ind in range(len(all_labels)):
        print(all_labels[ind], all_DOIs[ind], file=outfile)

    outfile.close()

    if "DOI_NOT_FOUND" in all_DOIs:
        rtfm("couldn't find all DOIs. Input file needs manual cleanup.")


def process_bibfile():
    """
    """
    myfile = open(INPUT_FILE, 'r')

    if OVERWRITE:
        outfile = open(BIB_FILE, 'w')
    else:
        outfile = open(BIB_FILE, 'a')

    all_labels = []

    for myline in myfile.readlines():
        if len(myline) < 2 or myline[0] == '#': # empty line or comment
            continue

        mysplit = myline.split(' ')

        label = None
        if len(mysplit) == 2:
            label = mysplit[0]
            if mysplit[1][-1] == "\n":
                DOI = mysplit[1][:-1] # remove the new line character
        else:
            if mysplit[0][-1] == "\n":
                DOI = mysplit[0][:-1]

        if DOI.lower().find('doi.org') > -1:
            DOI = DOI[DOI.lower().find('doi.org')+8:]

        exitcode, output = subprocess.getstatusoutput(
                f'curl -LH "Accept: application/x-bibtex" "http://dx.doi.org/' 
                                                        + DOI + '"')

        # skip to the relevant part of the output
        output = output[output.find('@'):]

        if label is None: # get label if it doesn't exist
            label = output[output.find('{')+1:output.find(',')]

            if label.lower().find('arxiv') > -1: # shorten arXiv auto-labels
                label = label[label.lower().find('arxiv'):]

        # check for repeated labels and correct if necessary 
        if label in all_labels:
            for letter in alphabet:
                if label+letter in all_labels:
                    continue
                else:
                    label = label+letter
                    all_labels.append(label)
                    break
        else:
            all_labels.append(label)

        # assign correct label
        output = output[:output.find('{')+1] + label + \
                                    output[output.find(','):]

        # handle arXiv entries separately
        if DOI.lower().find('arxiv') > -1:
            output = '@article' + output[output.find('{'):]
            bib_entry = pybtex.database.parse_string(output, "bibtex")
            bib_entry.entries[label].fields['pages'] = ' '
            bib_entry.entries[label].fields['journal'] = 'arXiv:' + \
                bib_entry.entries[label].fields['DOI'][
                    bib_entry.entries[label].fields['DOI'].find('/'):
                                                       ][7:]

            print(bib_entry.to_string('bibtex'))

            print(bib_entry.to_string('bibtex'), file=outfile)
            print('', file=outfile)
            continue


        # not an arXiv entry, move on
        bib_entry = pybtex.database.parse_string(output, "bibtex")

        # check for missing pages in articles
        if ("pages" not in bib_entry.entries[label].fields) and \
           (output[:8] == "@article"):
            # manually add pages for some papers
            manual_page_journals = ['Physical Review', 
                                    'Reviews of Modern Physics',
                                    'Science Advances'
                                    ]
            for mpj in manual_page_journals:
                if (bib_entry.entries[label].fields['journal'].find(
                                            mpj) > -1):
                    bib_entry.entries[label].fields['pages'] = \
                        bib_entry.entries[label].fields['DOI'][
                           bib_entry.entries[label].fields['DOI'].rfind('.')+1:
                                                               ]
                break

        # fix capitalization in titles
        try:
            bib_entry.entries[label].fields["title"] = "{" + \
                bib_entry.entries[label].fields["title"] + "}"
        except:
            pass


        print(bib_entry.to_string('bibtex'))
        print(bib_entry.to_string('bibtex'), file=outfile)
        print('', file=outfile)

    outfile.close()



























def main():
    """
    """
    parse_args()

    process_bibfile()

    abbreviate_journal_names(BIB_FILE)


if __name__ == '__main__':
    main()
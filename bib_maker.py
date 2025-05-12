# Copyright (c) 2025, I. C. Fulga. All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met:
#
#     1) Redistributions of source code must retain the above copyright
#     notice, this list of conditions and the following disclaimer.
#
#     2) Redistributions in binary form must reproduce the above
#     copyright notice, this list of conditions and the following
#     disclaimer in the documentation and/or other materials provided
#     with the distribution.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


import pandas
import numpy as np
import sys
import subprocess
import getopt
import pybtex
import string
from pybtex.database import parse_file, BibliographyData, Entry
from urllib.request import urlopen
import re
import os

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
  -o, --overwrite       Overwrite the output file.

  -h, --help            Print this message and exit.

  -v, --verbose         Print text showing current progress.

  -e, --experimental    Use the `lynx' terminal browser to scrape some journal
                        websites that cannot be easily accessed using urlopen.

  -f, --force           Proceed with processing the DOIs even if not all were
                        found in the bib file.

Note:
  - This has been written using pybtex version 0.24.0
  - If you find that some journal abbreviations are missing, please help me
    complete the list.

"""
)

DEBUG_MODE = True # set this to false in the final version

BIB_FILE = None
INPUT_FILE = None
OVERWRITE = False
VERBOSE = False
FORCE = False

if DEBUG_MODE:
    OVERWRITE = True
    VERBOSE = True
    FORCE = True


### SET THIS TO TRUE AT YOUR OWN PERIL !!! ###
EXPERIMENTAL = True

def rtfm(s):
    print( "bib_maker:", s)
    print( "Try 'bib_maker --help' for more information.")
    sys.exit(1)


def parse_args():
    global BIB_FILE, INPUT_FILE, OVERWRITE, VERBOSE, EXPERIMENTAL, FORCE

    try:
        opts, remaining_args = \
            getopt.getopt(sys.argv[1:],
                          "ohvef",
                          ["overwrite", "help", "verbose",
                           "experimental", "force"])
    except getopt.GetoptError:
        rtfm("unrecognized option")

    try:
        INPUT_FILE = remaining_args[0]
        BIB_FILE = remaining_args[1]
    except:
        rtfm("missing in/out file")

    if INPUT_FILE[-4:] == '.bbl':
        extract_input_from_bbl(INPUT_FILE)
        INPUT_FILE = 'temp.txt'

    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            sys.exit()
        if o in ("-o", "--overwrite"):
            OVERWRITE = True
        if o in ("-v", "--verbose"):
            VERBOSE = True
        if o in ("-e", "--experimental"):
            EXPERIMENTAL = True
        if o in ("-f", "--force"):
            FORCE = True


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

        if not found_abbreviation and VERBOSE:
            print(f"{item.fields['journal']} not in list")

    bib.to_file(bibfile)


def get_DOI_from_arXiv(b2):
    """
    """
    DOI = 'DOI_NOT_FOUND'

    arXiv_numbers = re.findall(r'\d+', b2)
    try: # old arXiv papers have only one number, need to implement
        page = urlopen('https://arxiv.org/abs/' + 
                        arXiv_numbers[0] + '.' + 
                        arXiv_numbers[1])
        html_bytes = page.read()
        html = html_bytes.decode("utf-8")
        if html.find('data-doi="') > -1:
            html = html[html.find('data-doi="')+10:]
            DOI = html[:html.find('"')]

        elif html.find('id="arxiv-doi-link">') > -1:
            html = html[html.find('id="arxiv-doi-link">')+20:]
            DOI = html[:html.find('<')]
    except:
        pass
    
    return DOI


def get_DOI_using_lynx(url, site_type):
    """
    """
    sites_type_1 = ['sciencedirect.com',
                    ]

    if site_type in sites_type_1:
        os.system('lynx --source "' + url +
                  '" > temppage.html')

        journalsite = open('temppage.html', 'r')
        ft = ""
        for myline in journalsite.readlines():
            ft += myline

        journalsite.close()
        os.system('rm temppage.html')

        if ft.find('<meta name="citation_doi" content="') > -1:
            ft = ft[ft.find('<meta name="citation_doi" content="')+35:]
            DOI = ft[:ft.find('"')]
            return DOI

    return 'DOI_NOT_FOUND'


def get_pages_using_lynx(url, journal):
    """
    """
    journals_type_1 = ['Applied Physics Letters',
                       'Journal of Mathematical Physics',
                      ]

    if journal in journals_type_1:
        os.system('lynx --source "' + url +
                  '" > temppage.html')

        journalsite = open('temppage.html', 'r')
        ft = ""
        for myline in journalsite.readlines():
            ft += myline

        journalsite.close()
        os.system('rm temppage.html')

        if ft.find('"pageStart":"') > -1:
            ft = ft[ft.find('"pageStart":"')+13:]
            pages = ft[:ft.find('"')]
            return pages

    return None


def extract_input_from_bbl(bblfilename, 
                           outfilename='temp.txt'):
    """
    """
    if VERBOSE:
        print('### Extracting labels and DOIs from bbl file')
        print()

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

            if DOI.lower().find('arxiv') > -1:
                DOI = DOI[DOI.lower().find('arxiv'):]
                DOI = get_DOI_from_arXiv(b2)

        # try to find the DOI from the URL
        elif bibitem.find("\\href") > -1:
            b2 = bibitem[bibitem.find("\\href")+5:]
            b2 = b2[:b2.find("}")]

            # maybe the URL contains the DOI in it
            if b2.find("doi.org/") > -1:
                b2 = b2[b2.find("doi.org/")+8:]
                DOI = b2.strip()

                if DOI.lower().find('arxiv') > -1:
                    DOI = DOI[DOI.lower().find('arxiv'):]
                    DOI = get_DOI_from_arXiv(b2)


            elif b2.find("/10.") > -1 and b2[b2.find("/10.")+8] == "/":
                b2 = b2[b2.find("/10.")+1:]
                DOI = b2.strip()

                if DOI.lower().find('arxiv') > -1:
                    DOI = DOI[DOI.lower().find('arxiv'):]
                    DOI = get_DOI_from_arXiv(b2)


                # trim extra bits after the DOI in the URL
                if DOI.rfind("&") > -1:
                    DOI = DOI[:DOI.rfind("&")]
                if DOI.rfind("?") > -1:
                    DOI = DOI[:DOI.rfind("?")]

            # if there's an arXiv URL, scrape the website for the DOI
            # and if it's been already published then use the published DOI
            elif b2.find('arxiv.org/') > -1:
                b2 = b2[b2.find('arxiv.org/'):]
                DOI = get_DOI_from_arXiv(b2)

            # if it's a URL from nature.com, extract the DOI from it
            elif b2.find('www.nature.com/articles/') > -1:
                b2 = b2[b2.find('www.nature.com/articles/')+24:]

                if b2[-4:] == '.pdf':
                    b2 = b2[:-4]
                if b2.rfind('&') > -1:
                    b2 = b2[:b2.rfind('&')]
                if b2.rfind('?') > -1:
                    b2 = b2[:b2.rfind('?')]

                DOI = '10.1038/' + b2

            elif b2.find('sciencedirect.com') > -1:
                if EXPERIMENTAL:
                    if b2.find('{') > -1:
                        b2 = b2[b2.find('{')+1:]

                    DOI = get_DOI_using_lynx(b2.strip(), 'sciencedirect.com')

        # DOI not found using href, but there is an Eprint
        if DOI == 'DOI_NOT_FOUND' and bibitem.find("\\Eprint") > -1:
            b2 = bibitem[bibitem.find("\\Eprint")+7:]
            b2 = b2[:b2.find("}")]
            DOI = get_DOI_from_arXiv(b2)

        # DOI not found using href or Eprint, but maybe arXiv in journal name
        if DOI == 'DOI_NOT_FOUND' and bibitem.find("{journal}") > -1:
            b2 = bibitem[bibitem.rfind("{journal}")+9:]
            b2 = b2[:b2.find("}")]

            if b2.lower().find('arxiv:') > -1:
                b2 = b2[b2.lower().find('arxiv:'):]
                DOI = get_DOI_from_arXiv(b2)

        all_DOIs.append(DOI)
        
        if VERBOSE:
            print(label, DOI)


    outfile = open(outfilename, 'w')
    for ind in range(len(all_labels)):
        print(all_labels[ind], all_DOIs[ind], file=outfile)

    outfile.close()

    if ("DOI_NOT_FOUND" in all_DOIs) and (FORCE == False):
        rtfm("couldn't find all DOIs. Input file needs manual cleanup.")


def process_bibfile():
    """
    """

    if VERBOSE:
        print('### Processing input file')
        print()

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

        if DOI == 'DOI_NOT_FOUND':
            continue

        exitcode, output = subprocess.getstatusoutput(
                f'curl -LH "Accept: application/x-bibtex" "http://dx.doi.org/' 
                                                        + DOI + '"')

        # skip to the relevant part of the output
        output = output[output.find('@'):]

        # the DOI is wrong
        if output.find('This DOI cannot be found in the DOI System.') > -1:
            if VERBOSE:
                print('### ' + DOI + ' not found.')

            continue

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

            # fix capitalization in titles
            try:
                bib_entry.entries[label].fields["title"] = "{" + \
                    bib_entry.entries[label].fields["title"] + "}"
            except:
                pass

            if VERBOSE:
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
                                    'SciPost Physics',
                                    'Journal of the Physical Society of Japan',
                                    'PRX Quantum',
                                    ]

            for mpj in manual_page_journals:
                if (bib_entry.entries[label].fields['journal'].find(
                                            mpj) == 0):
                    bib_entry.entries[label].fields['pages'] = \
                        bib_entry.entries[label].fields['DOI'][
                           bib_entry.entries[label].fields['DOI'].rfind('.')+1:
                                                               ]

            # some pages need extra work when they are manually added
            manual_page_journals2 = ['Proceedings of the National Academy of Sciences', 
                                     'Science Advances',
                                     'Science',
                                    ]

            for mpj2 in manual_page_journals2:
                if (bib_entry.entries[label].fields['journal'].find(
                                            mpj2) == 0):
                    bib_entry.entries[label].fields['pages'] = 'e' + \
                        bib_entry.entries[label].fields['DOI'][
                           bib_entry.entries[label].fields['DOI'].rfind('.')+1:
                                                               ]

            manual_page_journals3 = ['Advanced Materials',
                                     'Advanced Functional Materials',
                                     'Advanced Materials Interfaces',
                                     'Small',
                                     ]

            for mpj3 in manual_page_journals3:
                if (bib_entry.entries[label].fields['journal'].find(
                                            mpj3) == 0):
                    bib_entry.entries[label].fields['pages'] = \
                        bib_entry.entries[label].fields['DOI'][
                           bib_entry.entries[label].fields['DOI'].rfind('.')+3:
                                                               ]


            # in some cases, get the pages by scraping the journal site
            scraping_page_journals = ['Nature Communications', 
                                      'Communications Physics',
                                      'npj Quantum Materials',
                                      'npj Computational Materials',
                                      'Science China Physics, Mechanics',
                                      'The European Physical Journal',
                                      'Journal of High Energy Physics', 
                                      'Scientific Reports',
                                      'Frontiers of Physics',
                                      ]

            for spj in scraping_page_journals:
                if (bib_entry.entries[label].fields['journal'].find(
                                                                    spj) == 0):
                    try:
                        page = urlopen('http://dx.doi.org/' + DOI)
                        html_bytes = page.read()
                        html = html_bytes.decode("utf-8")
                        html = html[html.find('"article-number">')+17:]
                        bib_entry.entries[label].fields['pages'] = \
                            html[:html.find('<')]
                    except:
                        pass

            # scraping some of the websites does not work directly in urlopen
            # so we use the terminal browser lynx
            experimental_page_journals = ['Applied Physics Letters',
                                          'Journal of Mathematical Physics',
                                          ]

            if EXPERIMENTAL:
                for epj in experimental_page_journals:
                    if (bib_entry.entries[label].fields['journal'].find(
                                                                    epj) == 0):
                        pages = get_pages_using_lynx('http://dx.doi.org/' 
                                                     + DOI, epj)
                        if pages is not None:
                            bib_entry.entries[label].fields['pages'] = pages

        # fix capitalization in titles
        try:
            bib_entry.entries[label].fields["title"] = "{" + \
                bib_entry.entries[label].fields["title"] + "}"
        except:
            pass


        # check if titles have mml:math and change to regular text
        if "title" in bib_entry.entries[label].fields:
            fix_title = True
            mytitle = bib_entry.entries[label].fields["title"]

            while fix_title:
                ind1 = mytitle.find('<mml')
                temptitle = mytitle[ind1+3:]
                ind2 = temptitle.find('>')
                if ind2 > -1 and ind1 > -1:
                    mytitle = mytitle[:ind1] + temptitle[ind2+1:]
                    fix_title = True
                else:
                    fix_title = False

            fix_title = True
            while fix_title:
                ind1 = mytitle.find('</mml')
                temptitle = mytitle[ind1+4:]
                ind2 = temptitle.find('>')
                if ind2 > -1 and ind1 > -1:
                    mytitle = mytitle[:ind1] + temptitle[ind2+1:]
                    fix_title = True
                else:
                    fix_title = False

            bib_entry.entries[label].fields["title"] = mytitle

        if VERBOSE:
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
#!/usr/bin/env -O python3
from omorfi import Omorfi
from glob  import glob
from sys import stdout, argv
import re
import gc

from argparse import ArgumentParser, FileType

previous = list()
sent = list()
max_window_size = 256

adjective_agreements = dict()
adposition_complements = dict()
adposition_complement_cases = ['CASE=GENITIVE', 'CASE=PARTITIVE', \
        'CASE=ELATIVE', 'CASE=ILLATIVE', 'CASE=ALLATIVE', 'CASE=ABLATIVE']

def add_to_sent(analyses, surf):
    global sent
    tags = set()
    for analysis in analyses:
        parts = analysis.output.split('][')
        for part in parts:
            tag = part.rstrip(']').lstrip('[')
            tags.add(tag)
        tags.add("SURF=" + surf)
    sent.append(tags)
    if 'BOUNDARY=SENTENCE' in tags:
        parse_sentence()
        previous = sent
        sent = list()
        gc.collect()
    elif len(sent) >= max_window_size:
        print("ERROR! Too long sentence chopped:")
        for coh in sent[:20]:
            for tag in coh:
                if tag.startswith("SURF="):
                    print(tag[len("SURF="):], end=' ')
        parse_sentence()
        sent = list()
        previous = list()
        gc.collect()

def extract_word_ids(word_pos):
    word_ids = ''
    for tag in sent[word_pos]:
        if tag.startswith('WORD_ID'):
            word_ids += tag[len('WORD_ID='):] + '/'
    return word_ids

def extract_surf(word_pos):
    return extract_tag(word_pos, 'SURF=')[len('SURF='):]

def extract_tag(word_pos, tagstart):
    for s in sent[word_pos]:
        if s.startswith(tagstart):
            return s

def context_adjective_agreement(word_pos):
    word = extract_surf(word_pos)
    if not word in adjective_agreements:
        adjective_agreements[word] = dict()
    case = extract_tag(word_pos, 'CASE=')
    comp_found = False
    if 'SUBCAT=ADJECTIVE' in sent[word_pos]:
        if word_pos < len(sent) - 1:
            #right_word = extract_word_ids(word_pos + 1)
            if 'POS=NOUN' in sent[word_pos + 1] and case in sent[word_pos + 1]:
                if not 'right' in adjective_agreements[word]:
                    adjective_agreements[word]['right'] = 1
                else:
                    adjective_agreements[word]['right'] += 1
            else:
                if not 'none' in adjective_agreements[word]:
                    adjective_agreements[word]['none'] = 1
                else:
                    adjective_agreements[word]['none'] += 1

def context_adposition_complement(word_pos):
    word = extract_surf(word_pos)
    if not word in adposition_complements:
        adposition_complements[word] = dict()
    comp_found = False
    if 'SUBCAT=ADPOSITION' in sent[word_pos]:
        if word_pos > 0:
            #left_word = extract_word_ids(word_pos - 1)
            for case in adposition_complement_cases:
                if 'POS=NOUN' in sent[word_pos - 1] and case in sent[word_pos - 1]:
                    if not 'left' in adposition_complements[word]:
                        adposition_complements[word]['left'] = dict()
                        adposition_complements[word]['left'][case] = 1
                    elif not case in adposition_complements[word]['left']:
                        adposition_complements[word]['left'][case] = 1
                    else:
                        adposition_complements[word]['left'][case] += 1
                    comp_found = True
        if word_pos < len(sent) - 1:
            #right_word = extract_word_ids(word_pos + 1)
            for case in adposition_complement_cases:
                if 'POS=NOUN' in sent[word_pos + 1] and case in sent[word_pos + 1]:
                    if not 'right' in adposition_complements[word]:
                        adposition_complements[word]['right'] = dict()
                        adposition_complements[word]['right'][case] = 1
                    elif not case in adposition_complements[word]['right']:
                        adposition_complements[word]['right'][case] = 1
                    else:
                        adposition_complements[word]['right'][case] += 1
                    comp_found = True
        if 'POSSESSIVE=1STSINGULAR' in sent[word_pos] or 'POSSESSIVE=2NDSINGULAR' in sent[word_pos] or 'POSSESSIVE=3RDAMBIGUOUS' in sent[word_pos] or 'POSSESSIVE=2NDPLURAL' in sent[word_pos] or 'POSSESSIVE=1STPLURAL' in sent[word_pos]:
            if not 'poss' in adposition_complements[word]:
                adposition_complements[word]['poss'] = 1
            else:
                adposition_complements[word]['poss'] += 1
            comp_found = True
        if not comp_found:
            if not 'none' in adposition_complements[word]:
                adposition_complements[word]['none'] = 1
            else:
                adposition_complements[word]['none'] += 1

def parse_sentence():
    for word_pos in range(len(sent)):
        if 'SUBCAT=ADPOSITION' in sent[word_pos]:
            context_adposition_complement(word_pos)
        elif 'SUBCAT=ADJECTIVE' in sent[word_pos]:
            context_adjective_agreement(word_pos)

def test_adposition_complements(logfile):
    for lemma, comps in adposition_complements.items():
        if not 'left' in comps and not 'right' in comps:
            print(lemma, "0 complements", file=logfile)
        biggest = 0
        if 'left' in comps:
            lefts = 0
            for case in adposition_complements[lemma]['left']:
                lefts += adposition_complements[lemma]['left'][case]
            biggest = lefts
        if 'right' in comps:
            rights = 0
            for case in adposition_complements[lemma]['right']:
                lefts += adposition_complements[lemma]['right'][case]
            if rights > biggest:
                biggest = rights
        if 'none' in comps and ('right' in comps or 'left' in comps):
            if adposition_complements[lemma]['none'] > biggest:
                print(lemma, biggest, "with complements", adposition_complements[lemma]['none'], "without", file=logfile)

def test_adjective_agreements(logfile):
    for lemma, comps in adjective_agreements.items():
        if not 'right' in comps:
            print(lemma, "without agreeing NPs", file=logfile)
        elif 'none' in comps and 'right' in comps:
            if adjective_agreements[lemma]['right'] < adjective_agreements[lemma]['none']:
                print(lemma, adjective_agreements[lemma]['right'], "agreements",
                        adjective_agreeements[lemma]['none'], 'without',
                        file=logfile)


def print_adposition_stats(logfile):
    print("surcface", "left", "poss", "right", "none", "total", sep='\t',
            file=logfile)
    for lemma, comps in adposition_complements.items():
        totals = {'all': 0}
        lefts = {'all': 0}
        poss = 0
        rights = {'all': 0}
        nones = 0
        for case in adposition_complement_cases:
            totals[case] = 0
            lefts[case] = 0
            rights[case] = 0
        if 'left' in comps:
            for case in adposition_complements[lemma]['left']:
                lefts['all'] += adposition_complements[lemma]['left'][case]
                totals[case] += adposition_complements[lemma]['left'][case]
                lefts[case] = adposition_complements[lemma]['left'][case]
        if 'right' in comps:
            for case in adposition_complements[lemma]['right']:
                rights['all'] += adposition_complements[lemma]['right'][case]
                totals[case] += adposition_complements[lemma]['right'][case]
                rights[case] = adposition_complements[lemma]['right'][case]
        if 'poss' in comps:
            poss += adposition_complements[lemma]['poss']
        if 'none' in comps:
            nones += adposition_complements[lemma]['none']
        totals['all'] = lefts['all'] + poss + rights['all'] + nones
        print(lemma,
                lefts['all'], poss, rights['all'], nones, totals['all'],
                file=logfile, sep='\t')
        print(lemma, 
                "%.2f %%" % (lefts['all'] / totals['all'] * 100), 
                "%.2f %%" % (poss / totals['all'] * 100), 
                "%.2f %%" % (rights['all'] / totals['all'] * 100),
                "%.2f %%" % (nones / totals['all'] * 100), 
                "%.2f %%" % (totals['all'] / totals['all'] * 100),
                file=logfile, sep='\t')
        for case in adposition_complement_cases:
            if totals[case] > 0:
                print("%s %s" %(lemma, case),
                        lefts[case], "–", rights[case], "–", totals[case],
                        file=logfile, sep='\t')
                print("%s %s %%" %(lemma, case), 
                        "%.2f %%" % (lefts[case] / totals[case] * 100), 
                        "–", 
                        "%.2f %%" % (rights[case] / totals[case] * 100),
                        "–", 
                        "%.2f %%" % (totals[case] / totals[case] * 100),
                        file=logfile, sep='\t')


def main():
    a = ArgumentParser()
    a.add_argument('-f', '--fsa', metavar='FSAFILE', required=True,
            help="HFST's optimised lookup binary data for the transducer to be applied")
    a.add_argument('-i', '--input', metavar="INFILE", type=str, required=True,
            dest="infile", help="source of analysis data")
    opts = a.parse_args()
    if opts.infile:
        test_corpora_files = [opts.infile]
    else:
        test_corpora_files = glob("*.text")
    adposition_log = open('adposition_complements.log', 'w')
    adposition_stats = open('adposition_complements_full.log', 'w')
    adjective_log = open('adjective_agreements.log', 'w')
    omorfi = Omorfi()
    omorfi.load_filename(opts.fsa)
    test_corpora = list()
    for test_corpus_file in test_corpora_files:
        try:
            test_corpora.append(open(test_corpus_file))
        except IOError as ioe:
            print("Failed to open corpus ", test_corpus_file, ":", ioe)
    for test_corpus in test_corpora:
        print('lines from', test_corpus)
        linen = 0
        for line in test_corpus:
            linen += 1
            if (linen % 1000000) == 0:
                print(linen, "...! Time to reload everything because memory is leaking very badly indeed!")
                previous = list()
                sent = list()
                omorfi = None
                omorfi = Omorfi()
                omorfi.load_filename(opts.fsa)
                gc.collect()

            if (linen % 10000) == 0:
                print(linen, "...")
            for punct in ".,:;?!()":
                line = line.replace(punct, " " + punct)
            for token in line.split():
                analyses = omorfi.analyse(token)
                add_to_sent(analyses, token)
    test_adposition_complements(adposition_log)
    print_adposition_stats(adposition_stats)
    test_adjective_agreements(adjective_log)
    exit(0)

if __name__ == '__main__':
    main()

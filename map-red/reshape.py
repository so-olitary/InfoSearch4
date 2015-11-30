#!/usr/bin/env python
# -*- coding: utf-8 -*-

from base64 import b64decode, b64encode
from itertools import groupby
from operator import itemgetter

import pymorphy2
import argparse
import hashlib
import codecs
import pprint
import json
import sys
import os


# import zipimport
# importer = zipimport.zipimporter('bs123.zip')


def reshape(dat_name, ndx_name, bin_name, len_name, archiver, use_hashes=True, use_json=True, verbose=False):
    """ Create the tree files:
        
        1. ( N_+_documents_lengthes )
        2. ( norm  offset  size_ids   [sizes_posits]   [sizes_hashes] )_concat-ed
        3. (backward_index_+_coords_+_hashes)_bin_archived_concat-ed
    """
    with open(bin_name, 'wb') as f_bin:
        with codecs.open(ndx_name, 'w', encoding='utf-8') as f_index:
            with codecs.open(dat_name, 'r', encoding='utf-8') as f_data:

                if use_json: print >>f_index, '{'
                for word, group in groupby((line.strip().split('\t') for line in f_data), key=itemgetter(0)):

                    word_ids = False
                    pos_lens, hss = [], []

                    if word != '$':
                        index = {}

                        if use_json: print >>f_index, '\t"%s" : ' % word
                        # gs = sorted(group, key=lambda x: int(x[1]))
                        gs = group
                    else:
                        gs = group

                    for g in gs:
                        splt = g[1:]

                        # 1. ( N    documents lengthes )
                        if (len(splt) == 1) and (word == u'$'):
                            coded = splt[0]
                
                            decoded = archiver.decode(b64decode(coded))

                            N = decoded[0]
                            ids = decoded[1:N+1]
                            lens = decoded[N+1:]

                            for i in xrange(1,len(ids)):
                                ids[i] += ids[i-1]

                            with open(len_name, 'w') as f_dlen:
                                print >>f_dlen, '%d\t%s' % ( N, ' '.join([ '%d,%d' % (did, dlen) for did, dlen in zip(ids, lens) ]) ),
            
                            del coded, decoded

                        # 2. json( word : (offset,size) )
                        elif (len(splt) >= 2):

                            if   len(splt) > 2 and int(splt[0]) == 0:
                                id, ids_b64, lens_b64 = splt

                            elif len(splt) > 2 and use_hashes:
                                id, pos_b64, hss_b64 = splt

                            elif len(splt) > 1 and not use_hashes:
                                id, pos_b64 = splt

                            else:
                                raise Exception('NO WORD IDS!!!')

                            if int(id) == 0:
                                # Получили все номера документов для данного слова
                                coded_ids  = b64decode( ids_b64)
                                coded_lens = b64decode(lens_b64)
                                del ids_b64, lens_b64

                                # if verbose: print archiver.decode(coded_ids)

                                # Записываем их в бинарный файл первыми
                                index['ids']  = (f_bin.tell(), len(coded_ids))
                                f_bin.write(coded_ids)
                                del coded_ids

                                # Затем количество позиций
                                index['lens'] = (f_bin.tell(), len(coded_lens))
                                f_bin.write(coded_lens)
                                del coded_lens

                                # Позиции
                                index['posits'] = [f_bin.tell(), 0]

                                word_ids = True

                            elif not word_ids:
                                raise Exception('NO WORD IDS!!!')

                            else:
                                id = (int(id) - 1)
                                if use_hashes:
                                    coded_pos, coded_hss = b64decode(pos_b64), b64decode(hss_b64)
                                    hss.append(coded_hss)
                                else:
                                    coded_pos = b64decode(pos_b64)

                                # if verbose: print archiver.decode(coded_pos)

                                pos_lens.append( len(coded_pos) )
                                # Записываем в бинарный файл                            
                                f_bin.write(coded_pos)
                                del coded_pos
                    
                    if word != '$':
                        # ('offset', 'size')
                        
                        # Уточняем количество
                        shifts = [ index['posits'][0] ]
                        for len_p in pos_lens:
                            shifts.append( len_p ) # shifts[-1] + 
                        index['posits'] = b64encode(archiver.code(shifts))
                        del shifts
                        # size = shifts[i+1] - shifts[i]

                        # В конце хэши
                        shifts = [ f_bin.tell() ]
                        for h in hss:
                            shifts.append( len(h) ) # shifts[-1] + 
                        index['hashes'] = b64encode(archiver.code(shifts))
                        # Записываем их в бинарный файл
                        for h in hss: f_bin.write(h)
                        # size = shifts[i+1] - shifts[i]
                        del hss

                        if use_json:
                            print >>f_index, json.dumps(index, sort_keys=True, indent=2,
                                                        ensure_ascii=False, encoding='utf-8'), ','
                        else:
                            print >>f_index, u'%s\t%s' % (word, u' '.join( u'%s,%d,%d' % (k,v[0],v[1]) if k in ["ids","lens"]
                                                                        else u'%s,%s' % (k,v)  for k,v in index.items()))
                if use_json:
                    print >>f_index, '\n\n"" : [] }\n'


import utils
import fib_archive
import s9_archive


if __name__ == '__main__':

    args = utils.parse_args()

    if  args.fib:
        # fib_archive = importer.load_module('fib_archive')
        archiver = fib_archive.FibonacciArchiver(args.fib)

    elif args.s9:
        # s9_archive = importer.load_module('s9_archive')
        archiver =  s9_archive.Simple9Archiver()

    reshape(args.dat_name, args.ndx_name, args.bin_name, args.len_name,
            archiver=archiver, use_hashes=args.use_hashes)

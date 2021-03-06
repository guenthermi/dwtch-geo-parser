#!/usr/bin/python3

import content_class

import re
import numpy as np
from urllib.parse import urlparse
import enchant

import sys
from databaseOutput import *
from reader import *
from databaseOutput import *

VALID_TOP_LEVELS = ['en', 'us', 'au', 'de', 'at', 'ch', 'org', 'com', 'edu', 'net', 'gov']

enchant_dicts = [enchant.Dict("en_US"), enchant.Dict("de_DE")]

def weight_quality(table, url):
	if len(table[0]) <= 5:
		return False
	if not measure_col_consistence(table):
		return False
	# if not clean_string_check(table):
	# 	return False
	if not url_check(table, url):
		return False
	return True

def measure_col_consistence(table):
	count = 0
	for i,column in enumerate(table):
		dist = content_class.get_distribution(column)
		if sum(dist) > 0:
			cov = max(dist) / sum(dist)
			if  cov < 0.7:
				count += 1
	if (count / len(table)) > 0.1:
		return False
	else:
		return True

def clean_string_check(table):
	valid = [content_class.PreClass.NUMBER,
		content_class.PreClass.GEO, 
		content_class.PreClass.NUMBER_TEXT]

	for column in table:
		dist = content_class.get_distribution(column)
		c = np.argmax(dist)
		if c == content_class.PreClass.GEO:
			for i, count in enumerate(dist):
				if (count > 0) and not (i in valid):
					return False
	return True


def url_check(table, url):
	if urlparse(url).hostname.split('.')[-1] not in VALID_TOP_LEVELS:
		return False
	return True

def clear_string(text):
	# print(text)
	return ''.join(c for c in text if c.isalpha())

def language_check(headers):
	if len(headers) < 0:
		return True
	count_valid = 0
	count_unvalid = 0
	for key in headers:
		splits = headers[key].split()
		words = [clear_string(split) for split in splits]
		for word in words:
			if len(word) > 2:
				valid = False
				for d in enchant_dicts:
					if d.check(word):
						count_valid += 1
						valid = True
						break
				if not valid:
					count_unvalid += 1
	if count_valid >= count_unvalid:
		return True
	else:
		return False

def main(argc, argv):
	DB_OUTPUT = 'output.db'
	if (argc == 4):
		db_output = DatabaseOutput(DB_OUTPUT)
		reader = TableReader(argv[3])
		print(reader.get_line_count(), argv[1], argv[2])
		while reader.get_line_count() <= int(argv[2]):
			print('get here', reader.get_line_count())
			table = reader.get_next_table()
			if reader.get_line_count() >= int(argv[1]):
				quality = weight_quality(table['relation'], table['url'])
				db_output.add_result(dict(), reader.get_line_count(), table['url'], dict(), [], [], quality, table['relation'])
	return

if __name__ == "__main__":
	main(len(sys.argv), sys.argv)

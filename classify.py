#!/usr/bin/python3

from reader import *
from gazetteer import *
from wikidata_lookup import *
from coverageScores import *
from rating import *
from databaseOutput import *
import preprocessor as pre
import geo_coder as coder

import ujson as json
import sys
import re
import gzip

HELP_TEXT = '\033[1mclassify.py\033[0m selector destination [dump]...'

GAZETTEER_INDEX_LOCATION = 'index.db'

WIKIDATA_LOOKUP_LOCATION = 'wikidata_extractor/wikidata.db'

COVERAGE_TREE_LOCATION = 'coverageTree.json'

RATES_FILE_LOCATION = 'categoryCounts.json'

DB_OUTPUT = 'output.db'


def post(table):
	return

def gazetteer_test(columns, gazetteer, tree, wikidata_lookup):
	result = dict()
	data = dict()
	MIN_NUM_FOUND_FACTOR = 0.7
	MIN_FEATURE_CLASS_FACTOR = 0.99

	for i, col in enumerate(columns['columns']):
		res, cov = gazetteer.lookup_column_fast(col[0])

		nodes = [({}, tree.get_origin(), len(set(col[0])))] # tuple of precondition, node, max_number
		while len(nodes) > 0:
			node = nodes[-1]
			nodes = nodes[:-1]
			max_number = node[2]
			max_feature_count = 0
			max_feature = ''
			# info_string = ''
			counts_response, value_type = res.count_feature_values(node[0], node[1]['feature'], node[1]['featureValues'], node[1]['featureValuesType'])
			if value_type == 'single':
				max_feature_count = counts_response
			if value_type == 'complex':
				if counts_response:
					max_feature = max(counts_response, key=counts_response.get)
					max_feature_count = counts_response[max_feature]
					# info_string = str(max_feature) + ' '
			if (max_feature_count / max_number) >= node[1]['lower_bound']:
				# info_string += 'cov: ' + str(max_feature_count / max_number)
				if (len(node[1]['successors']) == 0):
					index = columns['column_indices'][i]
					if index in result:
						result[index].append((node[1]['name'], max_feature, max_feature_count / max_number))
					else:
						result[index] = [(node[1]['name'], max_feature, max_feature_count / max_number)]
				for new_node in node[1]['successors']:
					precondition = node[0]
					if node[1]['feature']:
						precondition[node[1]['feature']] = max_feature
					nodes.append((precondition, new_node, max_feature_count))
		if columns['column_indices'][i] in result:
			# wikidata lookup test
			is_result = True
			wl_result = wikidata_lookup.lookup_classes(col[0])
			if (wl_result):
				for key in wl_result:
					if wl_result[key]:
						print('delete element')
						del result[columns['column_indices'][i]]
						is_result = False
						break
			if is_result:
				data[columns['column_indices'][i]] = res.get_result()
	return result, data

def choose_interpretation(classification, ratings):
	result = dict()
	for number in classification:
		new_interpretations = []
		best = (0, float('inf'))
		for i, interpretation in enumerate(classification[number]):
			count = ratings.get_count(interpretation[0], interpretation[1])
			if count < best[1]:
				best = (i, count)
		new_interpretations = [(x[0], x[1], x[2], i == best[0]) for i,x in enumerate(classification[number])]
		result[number] = new_interpretations
	return result

def process_table(table, lookup, wikidata_lookup, line_count, coverage_tree, ratings, out=False):
	res, headers, rubbish_rows = pre.process(table['relation'], table['url'])
	if (not res):
		return dict(), dict(), dict(), [], 0
	if len(res['columns']) > 0:
		res, data = gazetteer_test(res, lookup, coverage_tree, wikidata_lookup)
		res = choose_interpretation(res, ratings)
		coordinates = coder.get_coordinates(res, data, coverage_tree)
		return res, coordinates, headers, rubbish_rows, 1
	return dict(), dict(), headers, rubbish_rows, 1

def print_table(table, full=False):
	for i, col in enumerate(table[0]):
		if full:
			print('column ', table[1][i], ' :', col[0], ' pos: ', col[1])
		else:
			print(col[0])

def create_test_dump(dest, g, wl, coverage_tree, ratings, dumps, positive_size, negative_size):
	f = gzip.open(dest, 'w')
	p_output_size = 0
	n_output_size = 0
	for dump in dumps:
		reader = TableReader(dump)
		table = reader.get_next_table()
		while(table):
			line_count = reader.get_line_count()
			print('Process Table', line_count, '... OutputSize: Positive:', p_output_size, 'Negative:', n_output_size)
			res, coordinates, headers, rubbish_rows, quality = process_table(table, g, wl, reader.get_line_count(), coverage_tree, ratings)
			if quality:
				if res and (p_output_size < positive_size):
					f.write(bytes(json.dumps(table), 'UTF-8'))
					f.write(bytes('\n', 'UTF-8'))
					p_output_size += 1
				else:
					if n_output_size < negative_size:
						f.write(bytes(json.dumps(table), 'UTF-8'))
						f.write(bytes('\n', 'UTF-8'))
						n_output_size += 1
				if (p_output_size >= positive_size) and (n_output_size >= negative_size):
					break
			table = reader.get_next_table()
	return

def main(argc, argv):
	if (argc < 3):
		print(HELP_TEXT)
	else:
		g = Gazetteer(GAZETTEER_INDEX_LOCATION)
		wl = WikidataLookup(WIKIDATA_LOOKUP_LOCATION)
		coverage_tree = CoverageTree(COVERAGE_TREE_LOCATION)
		ratings = Ratings(RATES_FILE_LOCATION)

		if argv[1] == '--create_test_dump':
			create_test_dump(argv[2], g, wl, coverage_tree, ratings, argv[5:], int(argv[3]), int(argv[4]))
			return
		# determine target lines
		targets = [0, float('inf')]
		if argv[1].isdigit():
			targets = [int(argv[1]), int(argv[1])]
		if re.match('^[0-9]+-[0-9]+$', argv[1]):
			targets = list(map(lambda x: int(x), argv[1].split('-')))
		db_output = DatabaseOutput(argv[2])
		for arg in argv[3:]:
			reader = TableReader(arg)
			table = reader.get_next_table()
			while (table):
				line_count = reader.get_line_count()
				if (line_count >= targets[0]) and (line_count <= targets[1]):
					print('Process Table', line_count, '...')
					res, coordinates, headers, rubbish_rows, quality = process_table(table, g, wl, reader.get_line_count(), coverage_tree, ratings)
					db_output.add_result(res, line_count, table['url'], coordinates, headers, rubbish_rows, quality, table['relation'])

				table = reader.get_next_table()

if __name__ == "__main__":
	main(len(sys.argv), sys.argv)

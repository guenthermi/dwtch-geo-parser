#!/usr/bin/python3

from gazetteer import *

import sys

INDICES = GazetteerResult.FEATURE_INDICES

def _get_only_best_interpreations(interpretations):
	best = dict()
	for key in interpretations:
		value = interpretations[key]
		for entry in value:
			if entry[3]:
				best[key] = entry
	return best

def _filter_by_best(best_interpretations, data, lookup):
	filtered = dict()
	for index in data:
		best = best_interpretations[index]
		feature = best[1]
		column = data[index]
		filtered[index] = dict()
		for entry in column:
			term = entry
			geo_entities = column[entry]
			for entity in geo_entities:
				is_valid = True
				for node in lookup[best[0]]:
					if node['featureValuesType'] == 'empty':
						continue
					elif node['featureValuesType'] == 'specific':
						if entity[INDICES[node['feature']]] in node['featureValues']:
							continue
						else:
							is_valid = False
							break
					elif node['featureValuesType'] == 'all':
						if entity[INDICES[node['feature']]] == best[1]:
							continue
						else:
							is_valid = False
							break
					elif node['featureValuesType'] == 'minimum':
						if entity[INDICES[node['feature']]] > node['featureValues']:
							continue
						else:
							is_valid = False
							break
					else:
						print('Error: Unknown featureValuesType: ', node.featureValuesType)
						is_valid = False
				if is_valid:
					if term in filtered[index]:
						filtered[index][term].add(entity)
					else:
						filtered[index][term] = set({entity})
	return filtered


def _filter_by_feature_code(data):
	for index in data:
		# determine feature code counts
		codes = dict()
		for term in data[index]:
			subject = data[index][term]
			subject_codes = set()
			for entry in subject:
				subject_codes.add(entry[INDICES['featureCode']])
			for code in subject_codes:
				if code in codes:
					codes[code] += 1
				else:
					codes[code] = 1
		# determine max feature code
		max_feature_code = None
		for code in codes:
			if not max_feature_code:
				max_feature_code = code
			if codes[code] > codes[max_feature_code]:
				max_feature_code = code
		# filter entrys that do not have the max feature code
		for term in data[index]:
			subject = data[index][term]
			if len(subject) > 1:
				new_subject = set()
				for entry in subject:
					if entry[INDICES['featureCode']] == max_feature_code:
						new_subject.add(entry)
				if len(new_subject) > 0:
					data[index][term] = new_subject
	return data

def _get_center(column):
	g_sum_lat = 0
	g_sum_long = 0
	g_size = len(column)
	if g_size == 0:
		return (0,0)
	for term in column:
		size = len(column[term])
		sum_lat = 0
		sum_long = 0
		for entity in column[term]:
			sum_lat += entity[4]
			sum_long += entity[5]
		g_sum_lat += sum_lat / size
		g_sum_long += sum_long / size
	return (g_sum_lat / g_size), (g_sum_long / size)

def _choose_entities(data):
	result = dict()
	for index in data:
		column = data[index]
		center = _get_center(column)
		entities = dict()
		for term in column:
			best = min(column[term], key=lambda x: (x[4]-center[0])**2 + (x[5]-center[1])**2)
			entities[term] = (best[4], best[5])
		result[index] = entities
	return result


def get_coordinates(interpretations, data, coverage_tree):
	# get best
	best = _get_only_best_interpreations(interpretations)
	# filter entities by the semantic of the interpretation
	filtered = dict()
	filtered = _filter_by_best(best, data, coverage_tree.get_lookup())
	filtered = _filter_by_feature_code(filtered)
	# choose entities if there are still multiple possibilities
	choice = _choose_entities(filtered)

	return choice

def main(argc, argv):
	print('Hello World')

if __name__ == "__main__":
	main(len(sys.argv), sys.argv)

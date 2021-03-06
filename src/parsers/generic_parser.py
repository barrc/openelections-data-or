#!/usr/local/bin/python3
# -*- coding: utf-8 -*-

# The MIT License (MIT)
# Copyright (c) 2016 OpenElections
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all 
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE 
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE 
# SOFTWARE.

from collections import OrderedDict
import argparse
import csv
import sys
import re

office_lookup = {
	'PRESIDENT': 'President',
	'US SENATOR': 'U.S. Senate',
	'U.S. SENATE': 'U.S. Senate',
	'SENATOR': 'U.S. Senate',
	'HOUSE': 'U.S. House',
	'US REP': 'U.S. House',
	'U.S. HOUSE': 'U.S. House',
	'US REPRESENTATIVE': 'U.S. House',
	'REPRESENTATIVE': 'U.S. House',
	'REPRESENTATIVE IN CONGRESS': 'U.S. House',
	'REP IN CONGRESS': 'U.S. House',
	'SECRETARY OF STATE': 'Secretary of State',
	'TREASURER': 'State Treasurer',
	'STATE TREASURER': 'State Treasurer',
	'ATTORNEY GENERAL': 'Attorney General',
	'GOVERNOR': 'Governor',
	'STATE HOUSE': 'State House',
	'STATE REP': 'State House',
	'STATE REPRESENTATIVE': 'State House',
	'STATE SENATE': 'State Senate',
	'STATE SENATOR': 'State Senate',
	'MEMBER OF ASSEMBLY': 'State Assembly',
	'STATE ASSEMBLY': 'State Assembly',
	'AUDITOR': 'Auditor',
	'COMMISSIONER OF AGRICULTURE': 'Commissioner of Agriculture',
}


# Configure variables
outfileFormat = '{}__{}__{}__{}__precinct.csv'
partyPostfixRE = re.compile(" \(([A-Z]{3})\)$")

headers = ['county', 'precinct', 'office', 'district', 'party', 'candidate', 'votes']


def main():
	args = parseArguments()
	parser = GenericParser(args.path, args.date, args.state, args.county, args.isGeneral)

	parser.flipCandidateNames = args.flipCandidateNames
	parser.parse()

def parseArguments():
	parser = argparse.ArgumentParser(description='Turn a generic csv into an OE-formatted csv')
	parser.add_argument('date', type=str, help='Date of the election. Used in the generated filename.')
	parser.add_argument('state', type=str, help='Two-letter state code of the election. Used in the generated filename.')
	parser.add_argument('county', type=str, help='County of the election. Used in the generated filename.')
	parser.add_argument('path', type=str, help='Path to an generically-formatted CSV file.')

	# By default, the script will assume the file is a general, --general doesn't have to be specified (but can be).
	# If multiple arguments are passed, the last one wins.
	parser.add_argument('--primary', action='store_false', dest='isGeneral', help='Process the file as a primary (parties per office).')
	parser.add_argument('--general', action='store_true', dest='isGeneral', help='Process the file as a general (parties per candidate). This is the default.')
	parser.add_argument('--flipCandidateNames', action='store_true', dest='flipCandidateNames', help='Turn "Last, First" into more standard "First Last".')

	return parser.parse_args()


class GenericParser(object):
	def __init__(self, path, date, state, county, isGeneral):
		self.path = path
		self.date = date
		self.state = state
		self.county = county
		self.isGeneral = isGeneral
		self.csvLines = []

	def parse(self):
		with open(self.path, 'r') as csvfile:
			reader = csv.reader(csvfile, delimiter=',', quotechar='"')
			header = []
			office = ""
			district = ""
			party = ""
			for row in reader:
				if row[0]:
					if self.isGeneral:
						office, district = self.parseOfficeDistrict(row[0])
					else:
						office, district, party = self.parseOfficeDistrictParty(row[0])

					header = row

				elif row[1] == 'TOTAL':
					for index, votes in list(enumerate(row)):
						if index > 1 and row[index]:
							if header[index] not in ['Voters', 'Trnout', 'Turnout', 'Pct', '']:
								precinct = 'Total'
								normalizedOffice = self.normalizeOffice(office)
								candidate = header[index]

								if self.isGeneral:
									candidate, party = self.parseParty(candidate)

								self.csvLines.append([self.county, precinct, normalizedOffice, district, party, self.normalizeName(candidate), votes])

				else:
					for index, votes in list(enumerate(row)):
						if index > 1 and row[index]:
							if header[index] not in ['Voters', 'Pct', '']:
								normalizedOffice = self.normalizeOffice(office)
								precinct = row[1]
								candidate = "Total" if header[index] in ["Trnout", "Turnout"] else header[index]

								if self.isGeneral:
									candidate, party = self.parseParty(candidate)

								self.csvLines.append([self.county, precinct, normalizedOffice, district, party, self.normalizeName(candidate), votes])

		with open(self.outfileName(), 'w') as csvfile:
			w = csv.writer(csvfile, lineterminator='\n')
			w.writerow(headers)

			for row in self.csvLines:
				w.writerow(row)


	def parseOfficeDistrict(self, text):
		party = ""
		district = ""
		office = text.strip().upper()

		districtPrefixType1RE = re.compile(",? (\d+)\w\w DIST(RICT)?")
		districtPrefixType2RE = re.compile(",? DIST\.? (\d+)")

		m = districtPrefixType1RE.search(office) or districtPrefixType2RE.search(office)

		if m:
			district = m.group(1)
			office = office.replace(m.group(0), "") # Remove district from office

		return (office, district)

	def parseParty(self, text):
		party = ''

		m = partyPostfixRE.search(text)

		if m:
			party = m.group(1)
			text = text.replace(m.group(0), "") # Remove party from text

		return (text, party)

	def parseOfficeDistrictParty(self, text):
		party = ""
		district = ""
		office = text.strip().upper()

		districtPrefixType1RE = re.compile(",? (\d+)\w\w DIST(RICT)?")
		districtPrefixType2RE = re.compile(",? DIST\.? (\d+)")

		m = partyPostfixRE.search(office)

		if m:
			party = m.group(1)
			office = office.replace(m.group(0), "") # Remove party from text

		m = districtPrefixType1RE.search(office) or districtPrefixType2RE.search(office)

		if m:
			district = m.group(1)
			office = office.replace(m.group(0), "") # Remove district from office

		return (office, district, party)

	def normalizeOffice(self, office):
		try:
			strippedOffice = re.sub(r"\s+", " ", office)
			outOffice = office_lookup[strippedOffice.upper()] # Normalise the office
		except KeyError as e:
			print("Can't find the office '{}'. Did you forget to pass --primary?".format(office))
			sys.exit(1)

		return outOffice

	def normalizeName(self, name):
		abbreviations = {'WI': 'Write-ins', 'OV': 'Over Votes', 'UV': 'Under Votes', 'BVS': 'BVS'}

		if name in abbreviations:
			return abbreviations[name]

		name = name.title()

		mistakes = OrderedDict()
		mistakes['Write-Ins'] = 'Write-ins'
		mistakes['Iii'] = 'III'
		mistakes['Ii'] = 'Ii'
		mistakes['Defazio'] = 'DeFazio'
		mistakes['Mclane'] = 'McLane'
		mistakes['Undervotes'] = 'Under Votes'
		mistakes['Overvotes'] = 'Over Votes'

		for mistake, correction in mistakes.items():
			if mistake in name:
				name = name.replace(mistake, correction)

		if self.flipCandidateNames:
			if "," in name:
				components = name.split(",")
				components[0], components[1] = components[1], components[0] # Swap first two
				name = " ".join(components).strip()

		return name

	def outfileName(self):
		primaryOrGeneral = "general" if self.isGeneral else "primary"
		name = outfileFormat.format(self.date, self.state.lower(), primaryOrGeneral, self.county.lower())
		return name



# Default function is main()
if __name__ == '__main__':
	main()

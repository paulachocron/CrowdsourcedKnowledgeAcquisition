# import urllib2
from HTMLParser import HTMLParser

# response = urllib2.urlopen('http://python.org/')
# html = response.read()

from lxml import html
import requests
import csv
import nltk
import pandas
import urllib2
from json import loads
import math
import numpy as np
from nltk.stem import WordNetLemmatizer
import re
from bs4 import BeautifulSoup


def get_categories_winfo(words):
	first_cat = {}
	no_first_cat = {}
	no_cat = []
	nothing = []

	for word in words:
		try:
			page_def = requests.get('http://www.wordreference.com/definition/'+word)
			# page_trans = requests.get('http://www.wordreference.com/es/translation.asp?tranword='+n)
			tree_def = html.fromstring(page_def.content)
			# tree_trans = html.fromstring(page_trans.content)
		except requests.exceptions.RequestException as e:    # This is the correct syntax
			print n
			sys.exit(1)
				

		soup = BeautifulSoup(page_def.content, "lxml")

		# First, get only the definitions that relate to nouns

		spans = soup.find_all('span', {'class' : 'rh_empos'})
		if not [sp for sp in spans if 'n.' in sp.get_text()]:
			spans = soup.find_all('span', {'class' : 'rh_pos'})
		if [sp for sp in spans if 'n.' in sp.get_text()]:
			noun_defs = []
			page_text = page_def.content
			for i in range(len(spans)-1):
				parts = page_text.split(str(spans[i]).replace('"', "'"), 1)
				if 'n.' in spans[i].get_text():
					ndef = parts[1].split(str(spans[i+1]).replace('"', "'"), 1)
					noun_defs.append(ndef[0])
				if len(parts)>1:
					page_text = parts[1]
				else:
					page_text = parts[0]
			# decide if we want to use all of these or only the first one. I think only the first one should be enough.
			if noun_defs and 'rh_def' in noun_defs[0]:
				ndef = noun_defs[0]
			else:
				ndef = ""
		else:
			ndef = ""

		# The following code decides if categories are assigned to the first sense, or if there are categories at all
		if ndef == "":
			nothing.append(word)
		else:
			soupd = BeautifulSoup(ndef, "lxml")
			rhcats = soupd.find_all('span', {'class' : 'rh_cat'})
			if len(rhcats)==0:
				no_cat.append(word)
			else: 
				cats = [cat.get_text() for cat in rhcats]
			rhdef = soupd.find_all('span', {'class' : 'rh_def'})
			firstdef = BeautifulSoup(str(rhdef[0]), "lxml")
			catfirst = firstdef.find_all('span', {'class' : 'rh_cat'})
			if not catfirst:
				no_first_cat[word] = cats
			else:
				first_cat[word] = cats

	print "With cat in first def"
	print first_cat
	print "No cat in first def"
	print no_first_cat
	print "No cat"
	print no_cat
	print "Nothing"
	print nothing


########### This is the run for the final game set
hints = set()
taboos = set()
inc_cities = ()

#get the data
df = pandas.read_csv('FinalGameSet.csv')
mtaboos = df.tabooWords
df = df[df.role == 'describer']
messages = df.message

for t in mtaboos:
	if isinstance(t, basestring):
		t = t.replace(';', ' ').split()
		taboos.update(t)

for h in messages:
	for c in [',','.','_', '!','?']:
		h = h.replace(c, ' ').lower()
	hs = [w for w in h.split() if not w.startswith('no')]
 	hints.update(hs)
 	
for wordlist in [taboos]:
	lemmas = []
	for h in wordlist:
			# p = nltk.PorterStemmer()
		wnl = WordNetLemmatizer()
		h = wnl.lemmatize(h)
		lemmas.append(h)

	types = nltk.pos_tag(list(lemmas))
	nouns = set()
	adjectives = set()

	nouns = [wt[0] for wt in types if wt[1] in ['NN','IN']] # this seems not to be very good
	adjectives = set(wt[0] for wt in types if wt[1] == 'JJ' )

	get_categories_winfo(nouns)

################ OBTAIN DICTIONARY OF CATEGORIES FOR LIST OF HINTS ##################

def get_categories(wordlist):
	categories = {}
	wordcats = {}
	for n in nouns:
		try:
			page_def = requests.get('http://www.wordreference.com/definition/'+n)
			# page_trans = requests.get('http://www.wordreference.com/es/translation.asp?tranword='+n)
			tree_def = html.fromstring(page_def.content)
			# tree_trans = html.fromstring(page_trans.content)
		except requests.exceptions.RequestException as e:    # This is the correct syntax
		    print n
		    sys.exit(1)

		# We need some more processing here. Basically, verify if the first senses have labels.
		wordcats[n] = tree_def.xpath('//span[@class="rh_cat"]/text()')
	return wordcats


######################## THIS BUILDS A DICTIONARY WITH THE NUMBER OF OCCURRENCES #######################
	
def occurrences(cat_dicc):
	categories = {}
	for w in cat_dicc.keys():
		for c in cat_dicc[w]:
			if c in categories.keys():
				categories[c] = categories[c] + 1
			else:
				categories[c] = 1
	return categories

########################## GOOGLE NORMALIZED DISTANCE #############################

def getGND(word1, word2):
	return getScore(get_hits(word1), get_hits(word2), get_hits("the"), get_hits(word1+" "+word2))

def getScore(fx, fy, nStat, fxy):

	if fxy == 0:
		# no co-occurrence
		return 0.0

	if fx == fy and fx == fxy:
		# perfect co-occurrence
		return 1.0

	score = (max(math.log(float(fx)), math.log(float(fy))) - math.log(float(fxy))) / float(math.log(float(nStat)) - min(math.log(float(fx)), math.log(float(fy))))

 	# we need to invert the order of terms because GND scores relevant terms low
	score = math.exp(-1.0 * score)
	return score

def get_hits(term):

	url = "http://www.google.com/search?q=" + term
	user_agent = {'User-Agent': 'Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)'}

	try:
		page_def = requests.get(url, headers = user_agent, timeout = 5000)
		print page_def
		tree_def = html.fromstring(page_def.content)
	except requests.exceptions.RequestException as e:    # This is the correct syntax
		sys.exit(1)

	data = tree_def.xpath('//div[@id="resultStats"]/text()')
	hits = data[0].split()[1]
	if hits > 0:
		return float(hits.replace(',',''))
	else:
		return 0.000001

# print getGND('jazz', 'soup')


########################## GENERAL TESTING ###########################

# for sp in spans[0].children:
# 	print sp
# noun_defs = [sp for sp in spans if sp.get_text()=='n.']
# print noun_defs
# for defin in noun_defs:
# 	soup2
# soup2 = BeautifulSoup(str(spans[0]), "lxml")

# print soup2.find_all('span', {'class' : 'rh_cat'})
# create a list of lines corresponding to element texts
# lines = [span.get_text() for span in spans]


# definitions0 = tree_def.xpath('//span[@class="rh_def"]/text()')
# print definitions0
# definitions1 = tree_def.xpath('//span[@class="rh_def"]/span[@class="rh_cat"]/text()')
# print definitions1




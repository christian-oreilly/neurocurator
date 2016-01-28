#!/usr/bin/python3

__author__ = "Christian O'Reilly"

import sys
from PySide import QtGui, QtCore

import re
import parse
import operator
import os
from shutil import copyfile
import getpass
import pickle

from annotation import Annotation
from approximateMatchDlg import MatchDlg
from tagWidget import TagWidget, Tag

from pyzotero import zotero

class ZoteroTableModel(QtCore.QAbstractTableModel):

	def __init__(self, parent, checkIdFct, header = ['ID', 'Title', 'Creator', 'Year', 'Journal'], *args):
		QtCore.QAbstractTableModel.__init__(self, parent, *args)

		self.header = header
		self.nbCol = len(header)
		self.fields = {0:"ID", 1:"title", 2:"creators", 3:"date", 4:"publicationTitle"}
		self.checkIdFct = checkIdFct
		self.refList = []

	#@property
	#def zotLib(self):
	#	return self.__zotLib
	#
	#@zotLib.setter
	#def zotLib(self, zotLib):
	#	self.__zotLib = zotLib
	#	self.refList = [i['data'] for i in zotLib.everything(zotLib.top())]


	def loadCachedDB(self, libraryId, libraryrType, apiKey):
		try:
			with open(libraryId + "-" + libraryrType + "-" + apiKey + ".pkl", 'rb') as f:
				self.refList = pickle.load(f)
		except:
			self.refreshDB(libraryId, libraryrType, apiKey)


	def refreshDB(self, libraryId, libraryrType, apiKey):
		zotLib = zotero.Zotero(libraryId, libraryrType, apiKey)
		self.refList = [i['data'] for i in zotLib.everything(zotLib.top())]

		with open(libraryId + "-" + libraryrType + "-" + apiKey + ".pkl", 'wb') as f:
			pickle.dump(self.refList, f)


	def rowCount(self, parent = None):
		return len(self.refList)

	def columnCount(self, parent = None):
		return self.nbCol 


	def getID(self, row):
		return self.getID_fromRef(self.refList[row])


	def getID_fromRef(self, ref):
		DOI = self.getDOI_fromRef(ref)
		PMID = self.getPMID_fromRef(ref)
		if DOI != "":
			return DOI
		elif PMID != "":
			return "PMID_" + PMID
		else:
			return ""	


	def getDOI(self, row):
		return self.getDOI_fromRef(self.refList[row])

	def getDOI_fromRef(self, ref):

		# Standard way
		if "DOI" in ref:
			if ref["DOI"] != "":
				return ref["DOI"]

		# Some book chapter as a DOI but Zotero does not have DOI field
		# for book chapter type of publication. In these case, the DOI
		# can be added to the extra field as done for the PMID in pubmed.
		if "extra" in ref:
			for line in ref["extra"].split("\n"):
				if "DOI" in line:
					return line.split("DOI:")[1].strip()

		return ""


	def getPMID(self, row):
		return self.getPMID_fromRef(self.refList[row])

	def getPMID_fromRef(self, ref):
		try:
			for line in ref["extra"].split("\n"):
				if "PMID" in line:
					return line.split("PMID:")[1].strip()
			return ""
		except KeyError:
			return ""



	def getByIndex(self, ref, ind):

		try:
			if self.fields[ind] == "creators":
				authors = []
				for creator in ref[self.fields[ind]]:
					if creator["creatorType"] == "author":
						authors.append(creator["lastName"])
				return ", ".join(authors)

			elif self.fields[ind] == "ID":
				return self.getID_fromRef(ref)


			return ref[self.fields[ind]]
		except KeyError:
			return ""


	def data(self, index, role):
		if not index.isValid():
		    return None


		if role == QtCore.Qt.BackgroundRole:
			if self.checkIdFct(self.getID(index.row())):
				return QtGui.QBrush(QtGui.QColor(215, 214, 213), QtCore.Qt.SolidPattern)
			else:
				return None

		if role == QtCore.Qt.DisplayRole:
			try:
				return self.getByIndex(self.refList[index.row()], index.column())
			except KeyError:
				return ""
			

		return None


	def headerData(self, col, orientation, role):
		if orientation == QtCore.Qt.Horizontal and role == QtCore.Qt.DisplayRole:
		    return self.header[col]
		return None

	def sort(self, col, order):
		"""sort table by given column number col"""
		self.emit(QtCore.SIGNAL("layoutAboutToBeChanged()"))
		reverse = (order == QtCore.Qt.DescendingOrder)
		self.refList = sorted(self.refList, key=lambda x: self.getByIndex(x, col), reverse = reverse)
		self.emit(QtCore.SIGNAL("layoutChanged()"))

	def refresh(self):
		self.emit(QtCore.SIGNAL("layoutChanged()"))

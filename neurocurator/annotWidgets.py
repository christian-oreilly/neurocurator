#!/usr/bin/python3

__author__ = "Christian O'Reilly"

import re
from collections import OrderedDict
from difflib import SequenceMatcher
from os.path import join

import numpy as np
from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import (QMessageBox, QDialog, QLabel, QGridLayout,
                             QGroupBox, QLineEdit, QPushButton, QWidget,
                             QFrame, QTextEdit, QStackedWidget, QComboBox)

from nat.annotation import (TextLocalizer, FigureLocalizer, TableLocalizer,
                            EquationLocalizer, PositionLocalizer,
                            NullLocalizer,
                            Annotation)
from nat.utils import Id2FileName
from .approximateMatchDlg import MatchDlg
from .areaSelector import PDFAreaSelector, loadImage
from .jsonDlg import JSONDlg
from .uiUtilities import disableTextWidget, enableTextWidget
from .uiUtilities import errorMessage


class EditAnnotWgt(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_window = parent

        # Widgets
        self.annotationTypesCbo     = QComboBox(self)
        self.newAnnotationBtn       = QPushButton('New', self)
        self.duplicateAnnotationBtn = QPushButton('Duplicate', self)
        self.deleteAnnotationBtn    = QPushButton('Delete', self)
        self.viewJSONBtn            = QPushButton('View JSON', self)
        self.saveAnnotationBtn      = QPushButton('Save', self)
        self.commentEdt             = QTextEdit('', self)

        self.editAnnotWgt = OrderedDict([("text",     EditAnnotTextWgt(self)), 
                                         ("figure",   EditAnnotFigureWgt(self)), 
                                         ("table",    EditAnnotTableWgt(self)), 
                                         ("equation", EditAnnotEquationWgt(self)), 
                                         ("position", EditAnnotPositionWgt(self)),
                                         ("null",     EditAnnotNullWgt(self))])

        # We use the list to as a redundancy of the list of keys in annotTypesDict
        # because we want these to be ordered. 
        self.annotTypeLst     = list(self.editAnnotWgt.keys())

        self.annotationTypesCbo.addItems(self.annotTypeLst)

        self.editAnnotStack = QStackedWidget(self)

        for annotType in self.annotTypeLst:
            self.editAnnotStack.addWidget(self.editAnnotWgt[annotType])

        # Layout
        self.editAnnotGroupBox = QGroupBox()
        gridAddAnnotations = QGridLayout(self.editAnnotGroupBox)
        gridAddAnnotations.addWidget(QLabel('Annotation type', self), 2, 0)
        gridAddAnnotations.addWidget(self.annotationTypesCbo, 2, 1)
        gridAddAnnotations.addWidget(self.saveAnnotationBtn, 2, 2)
        gridAddAnnotations.addWidget(self.deleteAnnotationBtn, 2, 3)
        gridAddAnnotations.addWidget(self.newAnnotationBtn, 2, 4)
        gridAddAnnotations.addWidget(self.duplicateAnnotationBtn, 2, 5)
        gridAddAnnotations.addWidget(self.viewJSONBtn, 2, 6)

        gridAddAnnotations.addWidget(self.editAnnotStack, 3, 0, 1, 7)

        gridAddAnnotations.addWidget(QLabel('Comment', self), 4, 0)
        gridAddAnnotations.addWidget(self.commentEdt, 4, 1, 1, 6)
        self.setLayout(gridAddAnnotations)

        # Signals
        self.saveAnnotationBtn.clicked.connect(self.saveAnnotation)
        self.newAnnotationBtn.clicked.connect(self.newAnnotation)
        self.duplicateAnnotationBtn.clicked.connect(self.duplicateAnnotation)
        self.viewJSONBtn.clicked.connect(self.viewJSON)
        self.deleteAnnotationBtn.clicked.connect(self.main_window.deleteAnnotation)
        self.commentEdt.textChanged.connect(self.annotationChanged)
        self.annotationTypesCbo.currentIndexChanged.connect(self.setCurrentStack)

        self.main_window.selectedAnnotationChangedConfirmed.connect(self.annotationSelectionChanged)
        for wgt in self.editAnnotWgt.values():
            self.main_window.selectedAnnotationChangedConfirmed.connect(wgt.annotationSelectionChanged)
        self.main_window.annotationCleared.connect(self.clearAddAnnotation)
        self.main_window.savingNeeded.connect(self.savingNeeded)

        # Initial behavior
        self.deleteAnnotationBtn.setDisabled(True)
        self.viewJSONBtn.setDisabled(True)
        self.annotationTypesCbo.setCurrentIndex(0)
        self.setCurrentStack(0)
        self.annotationTypesCbo.setDisabled(True)

    def viewJSON(self):        
        form = JSONDlg()
        form.setJSON(self.currentAnnotation)
        if form.exec_() == QDialog.Accepted:
            return 

    def saveAnnotation(self):
        self.main_window.saveAnnotation()
        self.annotationTypesCbo.setDisabled(True)

        
    def selectAnnotType(self, annotType):
        
        ind = [no for no, a in enumerate(self.annotTypeLst) if a == annotType]
        if len(ind) != 1:
            raise ValueError("Invalid annotation type string.")
        ind = ind[0]

        self.annotationTypesCbo.setCurrentIndex(ind)
        self.annotationTypesCbo.setEnabled(False)


    def setCurrentStack(self, ind):
        self.editAnnotStack.setCurrentIndex(ind) 

        #for no in range(len(self.annotTypeLst)):
        #    self.editAnnotStack.setTabEnabled(no, no == ind)
    


    @pyqtSlot()
    def clearAddAnnotation(self):
        self.commentEdt.setText("")
        for widget in self.editAnnotWgt.values():
            widget.clearAnnotation()

    @property
    def detectAnnotChange(self):
        return self.main_window.detectAnnotChange


    def annotationTextChanged(self):
        if self.detectAnnotChange:
            self.main_window.setNeedSaving()


    def annotationChanged(self):
        if self.detectAnnotChange:
            self.main_window.setNeedSaving()


    @property
    def currentAnnotation(self):
        return self.main_window.currentAnnotation

    @currentAnnotation.setter
    def currentAnnotation(self, annotation):
        self.main_window.currentAnnotation = annotation


    @pyqtSlot()
    def annotationSelectionChanged(self):
        #self.deleteAnnotationBtn.setEnabled(True)
        self.newAnnotationBtn.setEnabled(True)
        self.duplicateAnnotationBtn.setEnabled(True)
        if not self.currentAnnotation is None:
            self.commentEdt.setText(self.currentAnnotation.comment)
            enableTextWidget(self.commentEdt)
        else:
            self.commentEdt.setText("")
            disableTextWidget(self.commentEdt)            
        
        self.deleteAnnotationBtn.setDisabled(self.currentAnnotation is None)
        self.viewJSONBtn.setDisabled(self.currentAnnotation is None)

    def newAnnotation(self):
        if self.main_window.newAnnotation() :
            self.newAnnotationBtn.setEnabled(False)
            self.duplicateAnnotationBtn.setEnabled(False)
            self.deleteAnnotationBtn.setEnabled(False)
            self.viewJSONBtn.setDisabled(False)
            self.annotationTypesCbo.setEnabled(True)
            self.clearAddAnnotation()
            for widget in self.editAnnotWgt.values():
                widget.newAnnotation()

            if "UNPUBLISHED" in self.main_window.IdTxt.text():
                self.annotationTypesCbo.setEnabled(False)
                self.setCurrentStack(self.annotTypeLst.index("null"))
                self.annotationTypesCbo.setCurrentIndex(self.annotTypeLst.index("null"))
            else:
                self.annotationTypesCbo.setEnabled(True)
            enableTextWidget(self.commentEdt)

    def duplicateAnnotation(self):
        self.main_window.duplicateAnnotation()



    @pyqtSlot(bool)
    def savingNeeded(self, needSaving):
        self.saveAnnotationBtn.setEnabled(needSaving)
        self.updateCurrentAnnotation()



    def updateCurrentAnnotation(self):
        if not self.currentAnnotation is None:
            self.currentAnnotation.comment = self.commentEdt.toPlainText()
            if not self.main_window.username in self.currentAnnotation.users:
                self.currentAnnotation.users.append(self.main_window.username)
            self.editAnnotWgt[self.annotationTypesCbo.currentText()].updateCurrentAnnotation()



class EditAnnotFigureWgt(QWidget):

    def __init__(self, container, parent=None):
        super().__init__(parent)

        self.container = container

        # Widgets
        self.noFigure                = QLineEdit('', self)
    
        # Signals
        self.noFigure.textChanged.connect(self.container.annotationChanged)

        # Layout
        self.editAnnotGroupBox = QGroupBox()
        gridAddAnnotations = QGridLayout(self.editAnnotGroupBox)
        gridAddAnnotations.addWidget(QLabel('Figure no.', self), 2, 0)
        gridAddAnnotations.addWidget(self.noFigure, 2, 1)

        self.setLayout(gridAddAnnotations)

        # Initial behavior
        self.editAnnotGroupBox.setDisabled(True)
        disableTextWidget(self.noFigure)

    @pyqtSlot()
    def annotationSelectionChanged(self):
        if not self.container.currentAnnotation is None:
            enableTextWidget(self.noFigure)
            if self.container.currentAnnotation.type == "figure":
                self.noFigure.setText(self.container.currentAnnotation.localizer.no)
        else:
            disableTextWidget(self.noFigure)
            self.noFigure.setText("")


    def newAnnotation(self):
        enableTextWidget(self.noFigure)


    def clearAnnotation(self):
        self.noFigure.setText("")


    def updateCurrentAnnotation(self):
        self.container.currentAnnotation.localizer = FigureLocalizer(self.noFigure.text())




class EditAnnotNullWgt(QWidget):

    def __init__(self, container, parent=None):
        super().__init__(parent)
        self.container = container

    @pyqtSlot()
    def annotationSelectionChanged(self):
        pass


    def newAnnotation(self):
        pass


    def clearAnnotation(self):
        pass


    def updateCurrentAnnotation(self):
        self.container.currentAnnotation.localizer = NullLocalizer()




class EditAnnotEquationWgt(QWidget):

    def __init__(self, container, parent=None):
        super().__init__(parent)

        self.container = container

        # Widgets
        self.noEquation                = QLineEdit('', self)
        self.pythonStringEdt        = QTextEdit('', self)
    
        # Signals
        self.noEquation.textChanged.connect(self.container.annotationChanged)
        self.pythonStringEdt.textChanged.connect(self.container.annotationChanged)

        # Layout
        self.editAnnotGroupBox = QGroupBox()
        gridAddAnnotations = QGridLayout(self.editAnnotGroupBox)
        gridAddAnnotations.addWidget(QLabel('Equation no.', self), 2, 0)
        gridAddAnnotations.addWidget(self.noEquation, 2, 1)

        gridAddAnnotations.addWidget(QLabel('Python representation', self), 3, 0)
        gridAddAnnotations.addWidget(self.pythonStringEdt, 3, 1)
        gridAddAnnotations.addWidget(QLabel('(optional)', self), 3, 2)

        self.setLayout(gridAddAnnotations)

        # Initial behavior
        self.editAnnotGroupBox.setDisabled(True)
        disableTextWidget(self.noEquation)
        disableTextWidget(self.pythonStringEdt)

    @pyqtSlot()
    def annotationSelectionChanged(self):

        if not self.container.currentAnnotation is None:
            enableTextWidget(self.noEquation)
            enableTextWidget(self.pythonStringEdt)
            if self.container.currentAnnotation.type == "equation":
                self.noEquation.setText(self.container.currentAnnotation.localizer.no)
                self.pythonStringEdt.setText(self.container.currentAnnotation.localizer.equation)
        else:
            disableTextWidget(self.noEquation)
            disableTextWidget(self.pythonStringEdt)
            self.noEquation.setText("")
            self.pythonStringEdt.setText("")


    def newAnnotation(self):
        enableTextWidget(self.noEquation)
        enableTextWidget(self.pythonStringEdt)


    def clearAnnotation(self):
        self.noEquation.setText("")
        self.pythonStringEdt.setText("")


    def updateCurrentAnnotation(self):
        pythonString = self.pythonStringEdt.toPlainText() if self.pythonStringEdt.toPlainText() != "" else None
        self.container.currentAnnotation.localizer = EquationLocalizer(self.noEquation.text(), pythonString)








class EditAnnotTableWgt(QWidget):

    def __init__(self, container, parent=None):
        super().__init__(parent)

        self.container = container

        # Widgets
        self.noTable                = QLineEdit('', self)
        self.noRow                    = QLineEdit('', self)
        self.noCol                    = QLineEdit('', self)
    
        # Signals
        self.noTable.textChanged.connect(self.container.annotationChanged)
        self.noRow.textChanged.connect(self.container.annotationChanged)
        self.noCol.textChanged.connect(self.container.annotationChanged)

        # Layout
        self.editAnnotGroupBox = QGroupBox()
        gridAddAnnotations = QGridLayout(self.editAnnotGroupBox)
        gridAddAnnotations.addWidget(QLabel('Table no.', self), 2, 0)
        gridAddAnnotations.addWidget(self.noTable, 2, 1)

        gridAddAnnotations.addWidget(QLabel('Row no.', self), 3, 0)
        gridAddAnnotations.addWidget(self.noRow, 3, 1)
        gridAddAnnotations.addWidget(QLabel('(optional)', self), 3, 2)

        gridAddAnnotations.addWidget(QLabel('Column no.', self), 4, 0)
        gridAddAnnotations.addWidget(self.noCol, 4, 1)
        gridAddAnnotations.addWidget(QLabel('(optional)', self), 4, 2)

        self.setLayout(gridAddAnnotations)

        # Initial behavior
        self.editAnnotGroupBox.setDisabled(True)
        disableTextWidget(self.noTable)

    @pyqtSlot()
    def annotationSelectionChanged(self):

        if not self.container.currentAnnotation is None:
            enableTextWidget(self.noTable)
            enableTextWidget(self.noRow)
            enableTextWidget(self.noCol)
            if self.container.currentAnnotation.type == "table":
                self.noTable.setText(self.container.currentAnnotation.localizer.no)
                self.noRow.setText(str(self.container.currentAnnotation.localizer.noRow))
                self.noCol.setText(str(self.container.currentAnnotation.localizer.noCol))
        else:
            disableTextWidget(self.noTable)
            disableTextWidget(self.noRow)
            disableTextWidget(self.noCol)
            self.noTable.setText("")
            self.noRow.setText("")
            self.noCol.setText("")


    def newAnnotation(self):
        enableTextWidget(self.noTable)
        enableTextWidget(self.noRow)
        enableTextWidget(self.noCol)
        #self.noTable.setFocus()

    def clearAnnotation(self):
        self.noTable.setText("")
        self.noRow.setText("")
        self.noCol.setText("")

    def updateCurrentAnnotation(self):
        noRow = self.noRow.text() if self.noRow.text() != "" else None
        noCol = self.noCol.text() if self.noCol.text() != "" else None
        self.container.currentAnnotation.localizer = TableLocalizer(self.noTable.text(), noRow, noCol)





class ImageThumbnail(QLabel):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundRole(QPalette.Base)
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        #self.setScaledContents(True)

    #def resizeEvent(self, event):
    #    img = QtGui.QPixmap()
    #    w   = self.width()
    #    h   = self.height()
    #    self.setPixmap(self.pixmap().scaled(w, h, Qt.KeepAspectRatio))


class EditAnnotPositionWgt(QWidget):

    def __init__(self, container, parent=None):
        super().__init__(parent)

        self.container = container

        # Widgets
        self.noPageTxt         = QLineEdit('', self)
        self.xTxt             = QLineEdit('', self)
        self.yTxt             = QLineEdit('', self)
        self.widthTxt         = QLineEdit('', self)
        self.heightTxt         = QLineEdit('', self)
        self.imgThumbnail   = ImageThumbnail(self)
        self.selectAreaBtn     = QPushButton('Select area', self)

        # Signals
        self.noPageTxt.textChanged.connect(self.container.annotationChanged)
        self.selectAreaBtn.clicked.connect(self.selectArea)

        # Layout
        self.editAnnotGroupBox = QGroupBox()
        gridAddAnnotations = QGridLayout(self.editAnnotGroupBox)
        gridAddAnnotations.addWidget(QLabel('Page no.', self), 2, 0)
        gridAddAnnotations.addWidget(self.noPageTxt, 2, 1)
        gridAddAnnotations.addWidget(QLabel('x', self), 3, 0)
        gridAddAnnotations.addWidget(self.xTxt, 3, 1)
        gridAddAnnotations.addWidget(QLabel('y', self), 4, 0)
        gridAddAnnotations.addWidget(self.yTxt, 4, 1)
        gridAddAnnotations.addWidget(QLabel('width', self), 5, 0)
        gridAddAnnotations.addWidget(self.widthTxt, 5, 1)
        gridAddAnnotations.addWidget(QLabel('height', self), 6, 0)
        gridAddAnnotations.addWidget(self.heightTxt, 6, 1)
        gridAddAnnotations.addWidget(self.selectAreaBtn, 7, 0, 1, 2)
        gridAddAnnotations.addWidget(self.imgThumbnail, 2, 2, 6, 1)

        gridAddAnnotations.setColumnStretch(0,1)
        gridAddAnnotations.setColumnStretch(1,1)
        gridAddAnnotations.setColumnStretch(2,3)

        self.setLayout(gridAddAnnotations)

        # Initial behavior
        self.editAnnotGroupBox.setDisabled(True)
        disableTextWidget(self.noPageTxt)
        disableTextWidget(self.xTxt)
        disableTextWidget(self.yTxt)
        disableTextWidget(self.widthTxt)
        disableTextWidget(self.heightTxt)


    @pyqtSlot()
    def annotationSelectionChanged(self):

        if not self.container.currentAnnotation is None:
            if self.container.currentAnnotation.type == "position":
                self.noPageTxt.setText(str(self.container.currentAnnotation.localizer.noPage))
                self.xTxt.setText(str(self.container.currentAnnotation.localizer.x))
                self.yTxt.setText(str(self.container.currentAnnotation.localizer.y))
                self.widthTxt.setText(str(self.container.currentAnnotation.localizer.width))
                self.heightTxt.setText(str(self.container.currentAnnotation.localizer.height))
                self.loadThumbnail()
        else:
            self.noPageTxt.setText("")
            self.xTxt.setText("")
            self.yTxt.setText("")
            self.widthTxt.setText("")
            self.heightTxt.setText("")
            self.imgThumbnail.clear()

    def newAnnotation(self):
        pass


    def clearAnnotation(self):
        self.noPageTxt.setText("")
        self.xTxt.setText("")
        self.yTxt.setText("")
        self.widthTxt.setText("")
        self.heightTxt.setText("")


    def updateCurrentAnnotation(self):
        self.container.currentAnnotation.localizer = PositionLocalizer(int(self.noPageTxt.text()), float(self.xTxt.text()), 
                                                                       float(self.yTxt.text()), float(self.widthTxt.text()), 
                                                                       float(self.heightTxt.text()))


    def selectArea(self):
        pdfFileName = join(self.container.main_window.dbPath, Id2FileName(self.container.main_window.IdTxt.text())) + ".pdf"
        self.selectAreaDlg = PDFAreaSelector(pdfFileName)
        self.selectAreaDlg.areaSelected.connect(self.updateSelectedArea)
        self.selectAreaDlg.exec_()


    @pyqtSlot()
    def updateSelectedArea(self):
        self.noPageTxt.setText(str(self.selectAreaDlg.currentPageInd+1))
        self.xTxt.setText(str(self.selectAreaDlg.x))
        self.yTxt.setText(str(self.selectAreaDlg.y))
        self.widthTxt.setText(str(self.selectAreaDlg.width))
        self.heightTxt.setText(str(self.selectAreaDlg.height))

        w   = self.imgThumbnail.width()
        h   = self.imgThumbnail.height()
        self.imgThumbnail.setPixmap(self.selectAreaDlg.image.scaled(w, h, Qt.KeepAspectRatio))

    def loadThumbnail(self):
        pdfFileName = join(self.container.main_window.dbPath, Id2FileName(self.container.main_window.IdTxt.text())) + ".pdf"
        pixmap = loadImage(pdfFileName,
                          self.container.currentAnnotation.localizer.noPage,
                          self.container.currentAnnotation.localizer.x,
                          self.container.currentAnnotation.localizer.y,
                          self.container.currentAnnotation.localizer.width,
                          self.container.currentAnnotation.localizer.height)
        self.imgThumbnail.setPixmap(pixmap)




class EditAnnotTextWgt(QWidget):

    def __init__(self, container, parent=None):
        super().__init__(parent)

        self.container = container

        # Widgets
        self.localizeBtn         = QPushButton('Localize', self)
        self.correctBtn         = QPushButton('Correct', self)
        self.textToAnnotateTxt = QLineEdit('', self)
        self.contextTxt         = QLineEdit('', self)
        self.startTxt         = QLineEdit('', self)
    
        # Signals
        self.localizeBtn.clicked.connect(self.localizeText)
        self.textToAnnotateTxt.returnPressed.connect(self.localizeText)
        self.textToAnnotateTxt.textEdited.connect(self.setLocalizable)
        self.correctBtn.clicked.connect(self.correctText)

        # Layout
        self.editAnnotGroupBox = QGroupBox()
        gridAddAnnotations = QGridLayout(self.editAnnotGroupBox)
        gridAddAnnotations.addWidget(QLabel('Annotated text', self), 2, 0)
        gridAddAnnotations.addWidget(self.textToAnnotateTxt, 2, 1, 1, 2)
        gridAddAnnotations.addWidget(QLabel('Context', self), 3, 0)
        gridAddAnnotations.addWidget(self.contextTxt, 3, 1, 1, 2)

        gridAddAnnotations.addWidget(QLabel('Starting character', self), 4, 0)
        gridAddAnnotations.addWidget(self.startTxt, 4, 1)
        gridAddAnnotations.addWidget(self.correctBtn, 4, 2)
        gridAddAnnotations.addWidget(self.localizeBtn, 4, 3)

        self.setLayout(gridAddAnnotations)

        # Initial behavior
        self.editAnnotGroupBox.setDisabled(True)
        disableTextWidget(self.textToAnnotateTxt)
        disableTextWidget(self.contextTxt)
        disableTextWidget(self.startTxt)
        self.localizeBtn.setDisabled(True)
        self.correctBtn.setDisabled(True)


    def correctText(self):
        enableTextWidget(self.textToAnnotateTxt)
        self.localizeBtn.setDisabled(True)
        self.correctBtn.setDisabled(True)

        


    def localizeText(self):
        def recursiveSearch(queryString, text, a=0, level=0, maxLevel=5):

            starts = [(a, m.start(), len(queryString)) for m in re.finditer(re.escape(queryString), text)]
            if len(starts) == 0:
                if level < maxLevel and len(queryString) > 4:
                    N = len(queryString)
                    starts = []
                    starts.extend(recursiveSearch(queryString[:int(N/2)], text, a,             level+1, maxLevel))
                    starts.extend(recursiveSearch(queryString[int(N/2):], text, a+int(N/2), level+1, maxLevel))
                    return starts
                else:
                    return starts
            else:
                return starts

        def processBlocks(blocks):
            for block in blocks:
                matcher = SequenceMatcher(None, queryStr, fileText[block["start"]:block["end"]])
                ratio = matcher.ratio()

                matcher.set_seq2(fileText[block["start"]-1:block["end"]])
                new_ratio = matcher.ratio()
                while new_ratio >= ratio and block["start"] > 0: 
                    block["start"] -= 1
                    ratio = new_ratio
                    matcher.set_seq2(fileText[block["start"]-1:block["end"]])
                    new_ratio = matcher.ratio()

                matcher.set_seq2(fileText[block["start"]+1:block["end"]])
                new_ratio = matcher.ratio()
                while new_ratio >= ratio and block["start"] < len(fileText)-1: 
                    block["start"] += 1
                    ratio = new_ratio
                    matcher.set_seq2(fileText[block["start"]+1:block["end"]])
                    new_ratio = matcher.ratio()

                matcher.set_seq2(fileText[block["start"]:block["end"]-1])
                new_ratio = matcher.ratio()
                while new_ratio >= ratio and block["end"] > 0: 
                    block["end"] -= 1
                    ratio = new_ratio
                    matcher.set_seq2(fileText[block["start"]:block["end"]-1])
                    new_ratio = matcher.ratio()

                matcher.set_seq2(fileText[block["start"]:block["end"]+1])
                new_ratio = matcher.ratio()
                while new_ratio >= ratio and block["end"] < len(fileText)-1: 
                    block["end"] += 1
                    ratio = new_ratio
                    matcher.set_seq2(fileText[block["start"]:block["end"]+1])
                    new_ratio = matcher.ratio()


                block["candidate"]     = fileText[block["start"]:block["end"]]
                block["ratio"]         = ratio
                block["candidate"]     = block["candidate"].replace("\n", " ")        

            return np.array([block for block in blocks if block["ratio"] > 0.5])


        if len(self.textToAnnotateTxt.text()) < 3:
            errorMessage(self, "Error", "The text to localized should be at least 3-character long.")
            return            

        txtFileName = join(self.container.main_window.dbPath, Id2FileName(self.container.main_window.IdTxt.text())) + ".txt"
    
        with open(txtFileName, 'r', encoding="utf-8", errors='ignore') as f :
            fileText = f.read()

        ## We try to find an exact match...
        starts = [m.start() for m in re.finditer(re.escape(self.textToAnnotateTxt.text()), fileText)]

        ## If now exact match was found...        
        if len(starts) == 0:

            ## We try to find approximate matches using difflib
            queryStr = self.textToAnnotateTxt.text()
            N = len(self.textToAnnotateTxt.text())
            #s = SequenceMatcher(None, queryStr, fileText)
            #matches = [match for match in s.get_matching_blocks()]    
            blocks = []
            #for match in matches:
            #    block                = {}
            #    block["start"]        = max(0, match.b-match.a)
            #    block["end"]        = min(block["start"]+N, len(fileText))
            #    blocks.append(block)
            #blocks = processBlocks(blocks)


            ## No approximate match was found using difflib
            if len(blocks) == 0:

                ## We try to find partial matches using a recursive algorithm that sequentially
                ## splits the query string and try to find these subsetrings
                blocks = []
                for a, b, size in recursiveSearch(queryStr, fileText):
                    start = max(0, b-a)
                    blocks.append({"start":start,
                                   "end"  :min(start+N, len(fileText))})
                blocks = processBlocks(blocks)

            u, indices = np.unique([str(block["start"]) + "-" + str(block["end"]) for block in blocks], return_index=True)
            blocks = blocks[indices]
            blocks = sorted(blocks, key=lambda match: match["ratio"], reverse=True)
            matchDlg = MatchDlg(blocks, fileText, self)
            if matchDlg.exec_() == QDialog.Accepted:
                starts = [matchDlg.chosenBlock["start"]]
            else:
                return

        elif len(starts) > 1:
            blocks = [{"start":m.start(), 
                       "end":m.start()+len(self.textToAnnotateTxt.text()), 
                       "candidate":self.textToAnnotateTxt.text()} for m in re.finditer(self.textToAnnotateTxt.text(), fileText)]
            matchDlg = MatchDlg(blocks, fileText, self)
            if matchDlg.exec_() == QDialog.Accepted:
                starts = [matchDlg.chosenBlock["start"]]
            else:
                return
        
        contextStart = starts[0] - self.container.main_window.contextLength
        contextEnd = starts[0] + len(self.textToAnnotateTxt.text()) + self.container.main_window.contextLength
        self.contextTxt.setText(fileText[contextStart:contextEnd])
        
        localizer = TextLocalizer(self.textToAnnotateTxt.text(), starts[0])

        # FIXME A new Annotation shouldn't be created here!!
        self.container.currentAnnotation = Annotation(self.container.commentEdt.toPlainText(), 
                                                    [self.container.main_window.username],
                                                    self.container.main_window.IdTxt.text(), localizer)

        self.startTxt.setText(str(starts[0]))
        ID = self.container.main_window.IdTxt.text()
        if ID in self.container.main_window.selectedTagPersist:
            #self.currentAnnotation.clearTags()
            for tagId in self.container.main_window.selectedTagPersist[ID]:
                self.container.currentAnnotation.addTag(tagId, self.container.main_window.dicData[tagId])

        self.localizeBtn.setDisabled(True)
        self.correctBtn.setDisabled(False)
        disableTextWidget(self.textToAnnotateTxt)
        enableTextWidget(self.container.commentEdt)
        self.container.main_window.tagAnnotGroupBox.setDisabled(False)
        self.container.main_window.refreshTagList()
        self.container.newAnnotationBtn.setEnabled(True)
        self.container.duplicateAnnotationBtn.setEnabled(True)
        self.container.commentEdt.setFocus()
        self.container.main_window.detectAnnotChange = True
        self.container.main_window.needSaving = True

    def clearAnnotation(self):
        self.textToAnnotateTxt.setText("")
        self.contextTxt.setText("")
        self.startTxt.setText("")

    @pyqtSlot()
    def annotationSelectionChanged(self):

        if not self.container.currentAnnotation is None:
            if self.container.currentAnnotation.type == "text":
                self.textToAnnotateTxt.setText(self.container.currentAnnotation.text)
                self.contextTxt.setText(self.container.main_window.getCurrentContext())
                self.startTxt.setText(str(self.container.currentAnnotation.start))    
                self.localizeBtn.setEnabled(False) 
                self.correctBtn.setEnabled(True)
                disableTextWidget(self.textToAnnotateTxt)
        else:
            self.textToAnnotateTxt.setText("")
            self.contextTxt.setText("")    
            self.startTxt.setText("")    
            self.correctBtn.setEnabled(False)

    def setLocalizable(self):
        self.localizeBtn.setDisabled(len(self.textToAnnotateTxt.text()) < 3)


    def newAnnotation(self):
        enableTextWidget(self.textToAnnotateTxt)
        #self.textToAnnotateTxt.setFocus()



    def updateCurrentAnnotation(self):
        try:
            self.container.currentAnnotation.localizer = TextLocalizer(self.textToAnnotateTxt.text(), int(self.startTxt.text()))
        except ValueError:
            msgBox = QMessageBox(self)
            msgBox.setWindowTitle("Invalid localizer")
            msgBox.setText("Before saving changes to this annotation, you must enter an \"Annotated text\" and then localize it.")
            msgBox.setStandardButtons(QMessageBox.Ok)
            msgBox.exec_()

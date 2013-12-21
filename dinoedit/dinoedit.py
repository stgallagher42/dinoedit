#!/usr/bin/python
# -*- coding: utf-8 -*-
import sys
import os
import math
from PyQt4 import QtGui, QtCore, uic
import qtresources
from blockhandler import BlockHandler

def applyXMLUI(name, obj):
        # This little function is only a tad bit simpler than several related globals
        uipath = os.path.join(os.path.dirname(sys.argv[0]), 'UI', '%s.ui' %name)
        uic.loadUi(uipath, obj)

qapp = QtGui.QApplication(sys.argv)

class DinoFileListWidget(QtGui.QListWidget):
        def __init__(self):
                # Dilemma.
                # 1) Create a custom menu on the spot, 
                # 2) Create a menu that is somehow altered to match the file (how?)
                # 3) Make a menu and a set of functions which will detect which file on-the-spot.
                # 3.1) Can we know where the menu was clicked or could we pass a variable? How does everyone else do it?
                pass
        
        def contextMenuEvent(event):
                # This is the function that creates the right-click menus for the main file list.
                pass

class DinoMain(QtGui.QMainWindow):
        def __init__(self):
                QtGui.QMainWindow.__init__(self)
                applyXMLUI('mainwindow', self)
                
                self.connect(self.actionQuit, QtCore.SIGNAL('triggered()'), self.close)
                self.connect(self.actionNew, QtCore.SIGNAL('triggered()'), self.newDocument)
                self.connect(self.actionLoad, QtCore.SIGNAL('triggered()'), self.loadDocument)
                self.connect(self.actionSave, QtCore.SIGNAL('triggered()'), self.saveDocument)
                self.connect(self.actionClose, QtCore.SIGNAL('triggered()'), self.closeDocument)
                self.connect(self.actionNextBlock, QtCore.SIGNAL('triggered()'), self.nextBlock)
                self.connect(self.actionPrevBlock, QtCore.SIGNAL('triggered()'), self.prevBlock)
                self.connect(self.actionRevertBlock, QtCore.SIGNAL('triggered()'), self.revertBlock)
                self.connect(self.actionNextFile, QtCore.SIGNAL('triggered()'), self.nextFile)
                self.connect(self.actionPrevFile, QtCore.SIGNAL('triggered()'), self.prevFile)
                self.connect(self.actionRevertFile, QtCore.SIGNAL('triggered()'), self.revertFile)
                self.connect(self.actionWordWrap, QtCore.SIGNAL('triggered( bool )'), self.wordWrap)
                self.connect(self.actionToggleLineTrimming, QtCore.SIGNAL('triggered( bool )'), self.toggleLineTrimming)
                self.connect(self.fileList, QtCore.SIGNAL('itemClicked( QListWidgetItem * )'), self.changeFile)
                self.connect(self.location, QtCore.SIGNAL('editingFinished()'), self.locationChanged)
                
                self.statsFlag = False # This is because QT won't tell us if the user changed the stats or we did - so we just rule ourselves out
                self.dl = DocumentList()
                self.newDocument()
        
        def newDocument(self):
                self.updateBlock(edit=True) # Save changes to previous file
                self.dl.addDocument(BlockHandler())
                self.revertFile()
                self.updateBlock(0)
                self.updateFileList()
                self.statusbar.showMessage("New untitled document opened.", 5000)
        
        def loadDocument(self):
                filename = QtGui.QFileDialog.getOpenFileName(None, 'File to open')
                if not filename:
                        # They canceled.
                        return
                self.updateBlock(edit=True) # Save changes to previous file
                self.dl.addDocument(BlockHandler(str(filename)))
                self.revertFile() # This loads the file info from scratch
                self.updateBlock(0)
                self.updateFileList()
                self.statusbar.showMessage('Opened "%s"' %os.path.basename(str(filename)), 5000)

        def saveDocument(self):
                # Grab the data onscreen
                self.updateBlock(edit=True)
                progress = QtGui.QProgressDialog('Saving changes to file. This can take a while for extremely large files.', 'Destructively Abort Saving', 0, self.dl.cdoc.meta.size_blocks)
                progress.setWindowModality(QtCore.Qt.WindowModal)
                for blocknum in self.dl.cdoc.save():
                        progress.setValue(blocknum)
                progress.setValue(self.dl.cdoc.meta.size_blocks)
                
                self.dl.cdoc.revert()
                # Now update it
                self.updateBlock(0)
        
        def closeDocument(self):
                if len(self.dl.getTitleList()) == 1:
                        # Can't drop to 0
                        c = self.dl.cdoc
                        self.newDocument()
                        self.dl.closeDocument(c.meta.formatted_title)
                else:
                        c = self.dl.cdoc
                        self.prevFile()
                        self.dl.closeDocument(c.meta.formatted_title)
                self.updateFileList()
        
        def locationChanged(self):
                self.updateBlock(int((self.location.value()/100)*self.dl.cdoc.meta.size_blocks))
        
        def wordWrap(self, b):
                if b:
                        self.mainEditor.setLineWrapMode(QtGui.QPlainTextEdit.WidgetWidth)
                else:
                        self.mainEditor.setLineWrapMode(QtGui.QPlainTextEdit.NoWrap)
        
        def toggleLineTrimming(self, b):
                self.dl.cdoc.trim_to_line = b
                #QtGui.QMessageBox
                self.revertFile()
                self.updateBlock()
        
        def nextBlock(self):
                self.updateBlock(n=1, r=True, edit=True)
        
        def prevBlock(self):
                self.updateBlock(n=-1, r=True, edit=True)
        
        def revertBlock(self):
                self.updateBlock()
        
        def updateBlock(self, n=None, r=False, edit=False):
                if not self.dl.cdoc:
                        # This must be the first file. Ignore it.
                        return
                
                if edit:
                        # Save the changes to the currently-viewed block
                        self.dl.cdoc.replaceBlock(self.dl.cdoc.meta.c_block, str(self.mainEditor.toPlainText()))
                
                if type(n) == int:
                        # Now move over a block or two...
                        self.dl.cdoc.meta.adjustCBlock(n, relative=r)
                
                # Load the text
                try:
                        self.mainEditor.setPlainText(self.dl.cdoc.getBlock())
                except: 
                        self.mainEditor.setPlainText(self.dl.cdoc.getBlock().decode())
                
                # This flag keeps the program from recursing
                #  causing it's own reaction to a change in the numbers
                self.statsFlag = True
                
                # Fill the boxes
                self.location.setValue(round(self.dl.cdoc.meta.location_percentage, 2))
                self.size.setText(self.dl.cdoc.meta.human_size_bytes)
                self.totalBlocks.setText(str(self.dl.cdoc.meta.size_blocks))
                self.editedBlocks.setText(str(self.dl.cdoc.meta.blocks_written))

                self.statsFlag = False

                # Update the previous/next buttons, but do not update the file list.
                # This is because changing the file list can cause problems with functions
                #  that are switching files.
                self.checkFileEnds()
        
        def nextFile(self):
                # Save changes to previously-viewed file
                self.updateBlock(edit=True) 
                # Switch document
                self.dl.nextDocument()
                # Load the text - update variables..
                self.updateBlock()
                # Show the change in the file list - move the highlighted part
                self.updateFileList()
        
        def prevFile(self):
                # Save changes to previously-viewed file
                self.updateBlock(edit=True) 
                # Switch document
                self.dl.prevDocument()
                # Load the text - update variables..
                self.updateBlock()
                # Show the change in the file list - move the highlighted part
                self.updateFileList()
        
        def revertFile(self):
                # Forget the changes to the entire file
                self.dl.cdoc.revert()
                # Load the first block again
                self.updateBlock(0)
        
        def changeFile(self, item):
                # This function responds to a click in the file list
                # Save the currently-viewed block
                self.updateBlock(edit=True)
                # Switch documents
                self.dl.toDocument(str(item.text()))
                # Load the next one
                self.updateBlock()
        
        def checkFileListEnds(self):
                # This fixes the previous and next buttons for the file list when switching files
                self.actionPrevFile.setEnabled(not self.dl.isBeginning())
                self.actionNextFile.setEnabled(not self.dl.isEnd())
        
        def checkFileEnds(self):
                # This is mostly an extension of update()
                # Enable/disable the next and previous buttons based on where we are
                self.actionPrevBlock.setEnabled(not self.dl.cdoc.meta.is_beginning)
                self.actionNextBlock.setEnabled(not self.dl.cdoc.meta.is_end)
        
        def updateFileList(self):
                # Rebuild the file list from scratch
                # Probably not very efficient, but it works
                self.checkFileEnds()
                self.checkFileListEnds()
                self.fileList.clear()
                self.fileList.addItems(self.dl.getTitleList())
                self.fileList.setCurrentRow(self.dl.indexByDoc(self.dl.cdoc))

class DocumentList:
        def __init__(self):
                self.documents = []
                self.cdoc = None
        
        def getTitleList(self):
                ''' Return document title list '''
                return [d.meta.formatted_title for d in self.documents]
        
        def nextDocument(self):
                self.cdoc = self.documents[self.documents.index(self.cdoc)+1]
        
        def prevDocument(self):
                self.cdoc = self.documents[self.documents.index(self.cdoc)-1]

        def toDocument(self, docname):
                self.cdoc = self.documents[self.getTitleList().index(docname)]
        
        def isBeginning(self):
                return self.cdoc is self.documents[0]
        
        def isEnd(self):
                return self.cdoc is self.documents[-1]
        
        def indexByDoc(self, doc):
                return self.getTitleList().index(doc.meta.formatted_title)
        
        def addDocument(self, doc):
                ''' This adds titles and stuff as necessary '''
                
                samenames = [d for d in self.documents if d.meta.title == doc.meta.title]
                if samenames:
                        doc.meta.formatted_title = '%s (%i)' %(doc.meta.title, len(samenames))
                else:
                        doc.meta.formatted_title = doc.meta.title
                
                self.documents.append(doc)
                self.cdoc = doc
        
        def closeDocument(self, docname=None):
                if docname:
                        del self.documents[self.getTitleList().index(docname)]
                else:
                        self.documents.remove(self.cdoc)

if __name__ == '__main__':
        d = DinoMain()
        d.show()
        qapp.exec_()

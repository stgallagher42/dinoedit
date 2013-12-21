# -*- coding: utf-8 -*-
import sys # for argv and path
import os # for stat() and path
from tempfile import TemporaryFile, NamedTemporaryFile
import pdb
from filemeta import FileMeta

class BlockHandler:
        def __init__(self, filename='', blocksize=4096):
                ''' Rudimentary file backend - needs improvement '''
                self.blocksize = blocksize
                self.filename = filename
                if filename:
                        self.fileobj = open(filename, 'r+b')
                else:
                        self.fileobj = TemporaryFile()
                
                # These flags adjust how the file is written/read
                # sparse has no real effect (yet)
                self.sparse = False
                self.trim_to_line = False

                self.meta = FileMeta(filename, blocksize)
                
                self.revert()
        
        def getBlock(self, n=None):
                ''' Wrapper around normal block-getter '''
                # Fix empty n
                n = n or self.meta.c_block
                # Inform meta
                self.meta.reading(n)
                
                # Optionally use line trim function
                if self.trim_to_line:
                        return self.trimWrapper(n)
                else:
                        return self._getBlock(n)
        
        def _getBlock(self, n):
                ''' Get the text of any block in the file. Reading beyond the end should be fine in theory. '''
                
                # Get a new block
                if n in self.changed_blocks:
                        # They should always see the same changed block
                        return self.changed_blocks[n]
                else:
                        # They have not changed the block; get them a new one
                        self.fileobj.seek(self.blocksize*n)
                        return self.fileobj.read(self.blocksize)
        
        def trimWrapper(self, n, break_start=True, break_end=True):
                ''' Get blocks, but try to start and end on newlines '''
                
                # Get the text - but avoid negative block numbers
                if n:
                        prevblock = self._getBlock(n-1)
                        prevblock_split = prevblock.splitlines()
                else:
                        prevblock = ''
                        prevblock_split = ['']
                thisblock = self._getBlock(n)
                thisblock_split = thisblock.splitlines()

                # Set up flags for breaking up the text
                break_in_prev = len(prevblock_split) > 1
                break_in_this = len(thisblock_split) > 1
                
                
                # Trim both blocks, then add together
                if all([break_in_this, break_in_prev, break_start, break_end]):
                        # Both have newlines, so piece them back together
                        # but don't insert a newline between them
                        return '\n'.join(prevblock_split[-1:]) + '\n'.join(thisblock_split[:-1])
                elif break_in_this and break_end:
                        # Only this block has a newline
                        return '\n'.join(thisblock_split[:-1])
                elif break_in_prev and break_start:
                        # Only that block has a newline
                        return prevblock_split[-1] + thisblock
                else:
                        # No newlines at all, just return the block
                        # Also happens on the first block
                        # And at the end block when the previous block has no newlines
                        return thisblock
                
        def replaceBlock(self, n, s):
                ''' Virtually save a block - but don't do much with it yet '''
                if self.getBlock(n) != s:
                        self.meta.dirtying(blocknum=n, lenmatch=len(self.getBlock(n)) == len(s))
                        self.changed_blocks[n] = s
        
        def save(self, save_to_filename=''):
                # This pieces together the changed and unchanged blocks.
                self.meta.cleaning()
                
                # Save /time/. Do nothing for unchanged files.
                if not self.changed_blocks:
                        return
                
                save_to_filename = save_to_filename or self.filename
                ofile = open(save_to_filename, 'r+b')
                
                kl = list(self.changed_blocks.keys())
                # This converts the is-the-(next/previous)-block-modified test to an O(1) instead of an O(n)
                # but who knows the O() for sort()?
                kl.sort()
                if self.trim_to_line:
                        # Line up the blocks to the original lines when trimming by loading their neighbors
                        # Make sure not to clobber other blocks if they were changed too
                        for changednum, blocknum in enumerate(kl):
                                # Setup easy to understand flags instead of lengthy conditionals
                                first_block =		blocknum == 0
                                last_block =		blocknum == self.meta.size_blocks
                                first_changed =		changednum == 0
                                last_changed =		changednum == len(kl)
                                first_consec_changed = (blocknum+1) != kl[changednum+1]
                                second_consec_changed = (blocknum-1) != kl[changednum-1]
                                
                                
                                if not first_block and (first_changed or second_consec_changed ):
                                        # Get the previous block, without the trimming so it lines up
                                        self.changed_blocks[blocknum-1] = self.trimWrapper(blocknum-1, break_start=False)
                                if not last_block and (last_changed or first_consec_changed ):
                                        # Same for the next block
                                        self.changed_blocks[blocknum+1] = self.trimWrapper(blocknum+1, break_end=False)
                                        
                offset = 0
                next_changed_block = 0
                for n in range(0, int(self.size_blocks+1), 1):
                        # +1 because reading beyond the end raises no error - but it might require testing to see exactly where we need to stop
                        if not n % 100:
                                # Update the progressbar
                                yield n
                        # Originally this was "n in kl" but the following is O(1) instead
                        if next_changed_block < len(kl) and n == kl[next_changed_block]:
                                # No need to seek - the write will do it
                                # Still must calculate
                                offset += (len(self.changed_blocks[n]) - self.blocksize)
                                try:
                                        ofile.write(self.changed_blocks[n])
                                except:
                                        ofile.write(self.changed_blocks[n].encode())
                                # Move to the next changed block
                                next_changed_block += 1
                        else:
                                # "if offset" means that we can skip rewriting
                                # then file hasn't changed here and the previous parts line up
                                # We still must seek
                                self.fileobj.seek((n*self.blocksize)+offset)
                                if offset: ofile.write(self.fileobj.read(self.blocksize))
                ofile.truncate(ofile.tell())
                ofile.flush()
                ofile.close()
                
        def revert(self):
                # Revert (or forget) changes. This does not always lose data; you can do this after a save too.
                self.meta.cleaning()
                self.changed_blocks = {}
                if self.filename:
                        self.size_bytes = os.stat(self.filename).st_size
                else:
                        self.size_bytes = 0
                self.size_blocks = self.size_bytes/self.blocksize
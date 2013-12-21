# -*- coding: utf-8 -*-
import os
import math # for log()

class FileMeta:
        ''' This class keeps a lot of statistics for use elsewhere
                size_blocks  :  # of blocks in the file, at max
                size_bytes   :  # of bytes in the file in the file system
                human_size_bytes, human_size_blocks: Easier to read format of the above
                dirty_blocks :  # of blocks that need to be written because of length changes
                blocks_written: # of blocks that need to be written anyway
                c_block      :  Current block #
                location_percentage: Current block in percentage of the file
                
                '''
        def __init__(self, filename, blocksize):
                # These are useful everywhere
                self.filename = filename
                self.blocksize = blocksize
                
                # These are for inclusion in the document list
                if self.filename:
                        self.title = str(os.path.basename(self.filename))
                else:
                        self.title = 'Untitled'
                self.formatted_title = self.title
                
                # This gives a hint to the length of a temporary file or a heavily written file
                self.max_read_block = -1
                self.c_block = 1
                
                # Revert file data
                self.update()
                self.cleaning()
        
        def dirtying(self, blocknum, lenmatch):
                ''' Call whenever a block becomes dirty.
                        must not be called before the first update() (which is in __init__) '''
                # Always a block written
                self.blocks_written += 1
                # Possibly update the minimum length mismatch for estimating write time
                if not lenmatch:
                        self.min_mismatch_written_block = min(blocknum, self.min_mismatch_written_block)
                        self.dirty_blocks = self.size_blocks - self.min_mismatch_written_block
        
        def cleaning(self):
                ''' Reset the file to completely clean '''
                self.min_mismatch_written_block = self.size_blocks
                self.blocks_written = 0
        
        def reading(self, blocknum):
                ''' Set which block is currently being read '''
                self.max_read_block = max(blocknum, self.max_read_block)
                self.adjustCBlock(blocknum)
        
        def adjustCBlock(self, adjustment, relative=False):
                ''' Adjust self.c_block either relatively or absolutely.
                        Meanwhile update a few variables'''		
                # Keep out QT-based type troubles
                assert type(adjustment) == int

                if relative:
                        self.c_block += adjustment
                else:
                        self.c_block = adjustment
                
                # A change was made, and this function isn't called millions of times
                # So imply an update
                self.update()
                

        def updateSize(self):
                # Find the space taken in the filesystem (not exactly on-disk but close)
                self.size_bytes = 0 # Actually still 0 unless we know otherwise
                if self.filename: # Try to get length information from the file
                        self.size_bytes = os.stat(self.filename).st_size
                self.human_size_bytes = self.sizeToHuman(self.size_bytes)
                
                # Find the length of the file in blocks
                self.size_blocks = 1 # Must be at least one block to work correctly
                self.size_blocks = int(math.ceil(float(self.size_bytes) / float(self.blocksize)))
                # This includes added blocks that have not been written
                self.size_blocks = max(self.size_blocks, self.max_read_block, 1)
                self.human_size_blocks = self.sizeToHuman(self.size_blocks * self.blocksize)
                
                # Find the length of the file in human readable format
                size_in_bytes = self.size_blocks * self.blocksize
                
        
        def sizeToHuman(self, size_in_bytes):
                ''' Convert a size of bytes into a human readable format '''
                # Must be at lease one byte to avoid a math domain error
                radix = int(math.log(max(size_in_bytes, 1), 2)/10)
                mantissa = size_in_bytes / 2.0**(radix*10)
                suffix = ' KMGTPE'[radix]
                return '%3.1f %sB' %(mantissa, suffix)
        
        def update(self):
                ''' Update a lot of statistics '''
                self.updateSize()
                
                # Find how far we are through the file
                self.location_percentage = (float(self.c_block) / float(self.size_blocks)) * 100

                # Enable or sisable the previous/next buttons
                self.is_end = self.c_block == self.size_blocks
                self.is_beginning = self.c_block == 0
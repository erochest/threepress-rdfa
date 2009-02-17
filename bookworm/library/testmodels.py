from models import *
 
class MockEpubArchive(EpubArchive): 
    '''Mock object to expose some protected methods for testing purposes, and use
    overridden mock related classes with different storage directories.'''

    def get_author(self, opf):
        self.authors = self._get_authors(opf)
        return self.author

    def get_authors(self, opf):
        return self._get_authors(opf)

    def get_metadata(self, tag, opf):
        return self._get_metadata(tag, opf)

    def get_title(self, opf):
        return self._get_title(opf)

    def parse_stylesheet(self, css):
        return self._parse_stylesheet(css)

    def _blob_class(self):
        return MockEpubBlob

    def _image_class(self):
        return MockImageFile

class MockBinaryBlob(BinaryBlob):
    '''Mock object that uses a different storage directory'''
    def _get_pathname(self):
        return u'test-data/storage'        

class MockEpubBlob(EpubBlob):
    def _get_pathname(self):
        return u'test-data/storage'        

class MockImageFile(ImageFile):
    def _blob_class(self):
        return MockImageBlob
    def _get_pathname(self):
        return u'test-data/storage'        

class MockImageBlob(ImageBlob):
    def _get_pathname(self):
        return 'test-data/storage'        


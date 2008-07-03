from models import EpubArchive
 
class MockEpubArchive(EpubArchive): 
    '''Mock object to expose some protected methods for testing purposes.'''

    def xml_from_string(self, string):
        return self._xml_from_string(string)

    def get_author(self, opf):
        self.authors = self._get_authors(opf)
        return self.author()

    def get_authors(self, opf):
        return self._get_authors(opf)

    def get_metadata(self, tag, opf):
        return self._get_metadata(tag, opf)

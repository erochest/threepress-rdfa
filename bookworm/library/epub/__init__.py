class InvalidEpubException(Exception):
    '''Exception class to hold errors that occur during processing of an ePub file'''
    archive = None
    def __init__(self, *args, **kwargs):
        
        if 'archive' in kwargs:
            self.archive = kwargs['archive']
        
        super(InvalidEpubException, self).__init__(*args)
    
    def __str__(self):
        err = super(InvalidEpubException, self).__str__()
        if self.archive and self.archive.name:
            err += " [archive=%s]" % self.archive.name 
        return err



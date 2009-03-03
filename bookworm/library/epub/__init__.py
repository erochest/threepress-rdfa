class InvalidEpubException(Exception):
    '''Exception class to hold errors that occur during processing of an ePub file'''
    archive = None
    def __init__(self, *args, **kwargs):
        
        if 'archive' in kwargs:
            self.archive = kwargs['archive']
        
        super(InvalidEpubException, self).__init__(*args)
    


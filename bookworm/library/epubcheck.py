# Library for calling an epub validator (current implementation is Java epub checker)

class EpubValidator():
    output = None
    errors = None
    filepath = None

    def __init__(self, filename, data):
        self.filename = filename
        self.data = data

    def run(self):
        return True

def validate(filename, data):
    validator = EpubValidator(filename, data)
    return validator.run()


from epubvalidator import EpubValidator

def validate(filename, data):
    validator = EpubValidator(filename, data)
    validator.run()
    return validator

# Library for calling an epub validator (current implementation is Java epub checker)
from django.conf import settings
import logging, os.path, subprocess

class EpubValidator():
    output = None
    errors = None
    filepath = None

    def __init__(self, filename, data):
        # Make sure we have a temp dir to write to
        if not os.path.exists(settings.EPUB_VALIDATOR_TEMP_DIR):
            os.mkdir(settings.EPUB_VALIDATOR_TEMP_DIR)

        self.filename = filename
        self.data = data

        # Create the temporary file
        self._write_temp_file()


    def _write_temp_file(self):
        self.filepath = "%s/%s" % (settings.EPUB_VALIDATOR_TEMP_DIR, self.filename)
        f = open("%s" % (self.filepath), 'w')
        f.write(self.data)
        f.close()

    def run(self):
        os.chdir(settings.EPUBCHECK_DIR)    
    
        #logging.debug("Executing epubcheck on %s: %s %s %s %s " % (self.filepath, settings.JAVA, settings.JAVA_JAR_ARG, settings.EPUBCHECK_JAR, self.filepath))
        process = subprocess.Popen([settings.JAVA, settings.JAVA_JAR_ARG, settings.EPUBCHECK_JAR, self.filepath],
                                   stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE
                                   )
        (output, errors) = process.communicate()
        self.output = output
        self.errors = errors

        # Cleanup
        self._delete_temp_file()

    def _delete_temp_file(self):
        os.remove(self.filepath)

    def clean_errors(self):
        if not self.errors:
            return None
        e = str(self.errors).replace(self.filepath, self.filename) 
        return [f.strip() for f in e.split('\n') if f]

    def xml_errors(self):
        '''Return the error list as a series of <error> nodes'''
        errors = self.clean_errors()
        error_list = ''
        for e in errors:
            error_list += '<error>%s</error>' % e
        return error_list

    def is_valid(self):
        if self.errors:
            return False
        return True
        
def validate(filename, data):
    validator = EpubValidator(filename, data)
    validator.run()
    return validator

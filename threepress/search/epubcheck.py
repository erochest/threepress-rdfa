# Library for calling an epub validator (current implementation is Java epub checker)
from django.conf import settings
import logging, os.path, subprocess, re

class EpubValidator():
    output = None
    errors = None
    filepath = None

    def __init__(self, filename, data):
        # Make sure we have a temp dir to write to
        if not os.path.exists(settings.EPUB_VALIDATOR_TEMP_DIR):
            logging.info("Creating %s " % settings.EPUB_VALIDATOR_TEMP_DIR)
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
        logging.info("Wrote %s " % self.filepath)

    def run(self):
        logging.info("Changing to %s" % settings.EPUBCHECK_DIR)    
        os.chdir(settings.EPUBCHECK_DIR)    
    
        logging.debug("Executing epubcheck on %s: %s %s %s %s " % (self.filepath, settings.JAVA, settings.JAVA_JAR_ARG, settings.EPUBCHECK_JAR, self.filepath))
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
        logging.info("Deleting file %s " % self.filepath)
        os.remove(self.filepath)

    def clean_errors(self):
        if not self.errors:
            return None
        e = str(self.errors).replace(self.filepath, self.filename) 
        error_list = [f.strip() for f in e.split('\n') if f]        
        return '\n'.join(error_list)

def validate(filename, data):
    validator = EpubValidator(filename, data)
    validator.run()
    return validator

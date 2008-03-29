<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:opf="http://www.idpf.org/2007/opf"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    version="2.0">

  <!-- Expects a tei:chapter node -->
  <xsl:template name="chapter-name">
    <xsl:value-of select="concat('chapter-', position())" />
  </xsl:template>


  <!-- Expects a tei:chapter node -->  
  <xsl:template name="chapter-file">
    <xsl:variable name="chapter-name">
      <xsl:call-template name="chapter-name" />
    </xsl:variable>
    <xsl:value-of select="concat($chapter-name, '.html')" />
  </xsl:template>


</xsl:stylesheet>
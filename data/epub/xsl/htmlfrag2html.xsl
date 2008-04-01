<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:xhtml="http://www.w3.org/1999/xhtml" 
    version="2.0">

  <xsl:import href="epub-common.xsl" />
  <xsl:output method="html" encoding="utf-8" omit-xml-declaration="yes" indent="yes"/>

  <xsl:template match="/">
    <html xmlns="http://www.w3.org/1999/xhtml">
      <head>
        <title><xsl:value-of select="(//xhtml:h2)[1]" /></title>
      </head>
      <body>
        <xsl:apply-templates />
      </body>
    </html>
  </xsl:template>

  <xsl:template match="xhtml:div">
    <div xmlns="http://www.w3.org/1999/xhtml" >
      <xsl:for-each select="@*[not(name()='id')]">
        <xsl:copy-of select="." />
      </xsl:for-each>
      <xsl:apply-templates />
    </div>
  </xsl:template>


  <!-- Delete the useless duplicated ids that TEI generates -->
  <xsl:template match="@id">
  </xsl:template>

</xsl:stylesheet>

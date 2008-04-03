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
    <xsl:copy-of select="." />
  </xsl:template>


</xsl:stylesheet>

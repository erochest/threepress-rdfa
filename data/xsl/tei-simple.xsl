<?xml version="1.0" encoding="utf-8"?>
<xsl:stylesheet xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:teix="http://www.tei-c.org/ns/Examples" xmlns:html="http://www.w3.org/1999/xhtml" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0">

  <xsl:template match="tei:p">
    <p>
      <xsl:apply-templates />
    </p>
  </xsl:template>
</xsl:stylesheet>
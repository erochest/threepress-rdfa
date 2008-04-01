<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:ncx="http://www.daisy.org/z3986/2005/ncx/"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    xmlns:opf="http://www.idpf.org/2007/opf"
    xmlns:dc="http://purl.org/dc/elements/1.1/"
    xmlns:dcterms="http://purl.org/dc/terms/"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    version="2.0">

  <xsl:import href="epub-common.xsl" />
  <xsl:template match="/">
    <ncx:ncx version="2005-1">
      <ncx:head>
        <ncx:meta name="dtb:uid" content="{/tei:TEI/@xml:id}"/>
        <ncx:meta name="dtb:depth" content="1"/>
        <ncx:meta name="dtb:totalPageCount" content="0"/>
        <ncx:meta name="dtb:maxPageNumber" content="0"/>
      </ncx:head>      
      <ncx:docTitle>
        <ncx:text><xsl:apply-templates select="//tei:titleStmt/tei:title" /></ncx:text>
      </ncx:docTitle>
      <ncx:navMap>
        <ncx:navPoint id="navpoint-1" playOrder="1">
          <ncx:navLabel>
            <ncx:text>Title Page</ncx:text>
          </ncx:navLabel>
          <ncx:content src="title_page.html"/>
        </ncx:navPoint>  
        <xsl:apply-templates select="//tei:div[@type='chapter']" />
      </ncx:navMap>
    </ncx:ncx>
  </xsl:template>

  <xsl:template match="tei:div[@type='chapter']">

    <xsl:variable name="chapter-file">
      <xsl:call-template name="chapter-file" />
    </xsl:variable>
    
    <!-- Navpoint needs to be +1 on the chapter, to account for the title page -->
    <ncx:navPoint id="{concat('navpoint-', position() + 1)}" playOrder="{position() + 1}">
      <ncx:navLabel>
        <ncx:text><xsl:apply-templates select="tei:head" /></ncx:text>
      </ncx:navLabel>
      <ncx:content src="{$chapter-file}" />
    </ncx:navPoint>
  </xsl:template>
</xsl:stylesheet>
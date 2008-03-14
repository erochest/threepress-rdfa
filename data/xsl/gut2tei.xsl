<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    version="2.0">

    <xsl:output method="xml" encoding="utf-8" omit-xml-declaration="no" indent="yes"/>

    <xsl:template match="gutbook">
      <tei:TEI>
        <xsl:attribute name="xml:id">
        <xsl:value-of select="translate(normalize-space(//titlepage/title/text()), ' ', '-')"/>
        <xsl:text>_</xsl:text>
        <xsl:value-of select="translate(normalize-space(//titlepage/author/text()), ' ', '-')"/>
        </xsl:attribute>
	<xsl:apply-templates select="gutblurb"/>
	<xsl:apply-templates select="book"/>
      </tei:TEI>
    </xsl:template>

    <xsl:template match="gutblurb">
      <tei:teiHeader>
	<tei:fileDesc>
	  <tei:titleStmt>
	    <tei:title><xsl:apply-templates select="//frontmatter/titlepage/title/text()" /></tei:title>
            <tei:author><xsl:apply-templates select="//frontmatter/titlepage/author/text()" /></tei:author>
	  </tei:titleStmt>
	  <tei:publicationStmt>
	    <tei:publisher>threepress 0.1</tei:publisher>
	  </tei:publicationStmt>
          
          <tei:sourceDesc>
            <tei:p>Source information removed by request of originator</tei:p>
            <!-- Removed Gutenberg notice per their agreement -->
            <!-- <xsl:apply-templates select="para"/> -->
	  </tei:sourceDesc>

	</tei:fileDesc>
	</tei:teiHeader>
    </xsl:template>
    <xsl:template match="book">
      <tei:text>
	<xsl:apply-templates />
      </tei:text>
    </xsl:template>	
    <xsl:template match="frontmatter">
      <tei:front>
	<!-- [ front matter ... ] -->
	<xsl:apply-templates />
      </tei:front>
    </xsl:template>
    <xsl:template match="bookbody">
      <tei:body>
	<!-- [ body of text ... ] -->
	<xsl:apply-templates />
      </tei:body>
    </xsl:template>

    <xsl:template match="part">
      <tei:div type="part">
	<xsl:attribute name="xml:id">
	  <xsl:value-of select="generate-id()"/>
	</xsl:attribute>
	<xsl:apply-templates />
        <tei:pb/>
      </tei:div>
    </xsl:template>

    <xsl:template match="chapter">
      <tei:div type="chapter">
	<xsl:attribute name="xml:id">
	  <xsl:value-of select="generate-id()"/>
	</xsl:attribute>
	<xsl:apply-templates />
        <tei:pb/>
      </tei:div>
    </xsl:template>


    <xsl:template match="toc">
      <!-- ignore and generate out of content -->
    </xsl:template>


    <xsl:template match="titlepage/partnum">
      <tei:head><xsl:apply-templates /></tei:head>
    </xsl:template>

    <xsl:template match="chapnum">
      <tei:head>
        <xsl:if test="not(contains(./text(), 'apter')) and not(contains(./text(), 'APTER'))">
          Chapter
        </xsl:if>
        <xsl:apply-templates />
      </tei:head>
    </xsl:template>

    <xsl:template match="chapnum/title">
      <xsl:apply-templates />
    </xsl:template>

    <xsl:template match="title|partnum|">
      <tei:head><xsl:apply-templates /></tei:head>
    </xsl:template>

    <xsl:template match="frontmatter/titlepage">
      <tei:titlePage>
	<xsl:apply-templates />
      </tei:titlePage>
    </xsl:template>

    <xsl:template match="bookbody/part/titlepage">
      <xsl:apply-templates />
    </xsl:template>


    <xsl:template match="titlepage/title">
      <tei:docTitle><tei:titlePart><xsl:apply-templates /></tei:titlePart></tei:docTitle>
    </xsl:template>


    <xsl:template match="bookbody/part/titlepage/title">
      <tei:head><xsl:value-of select="." /></tei:head>
    </xsl:template>


    <xsl:template match="titlepage/author">
      <tei:docAuthor><xsl:apply-templates /></tei:docAuthor>
    </xsl:template>

    <xsl:template match="titlepage/para">
    </xsl:template>

    <xsl:template match="para">
      <tei:p>
      <xsl:attribute name="xml:id">
	<xsl:value-of select="generate-id()"/>
      </xsl:attribute>
      <xsl:apply-templates /></tei:p>
    </xsl:template>

    <xsl:template match="backmatter">
      <tei:back>
	<tei:div>
	  <xsl:apply-templates />
	</tei:div>
      </tei:back>
    </xsl:template>

    <xsl:template match="acknowledge" />
</xsl:stylesheet>

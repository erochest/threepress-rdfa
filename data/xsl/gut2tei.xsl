<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet 
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
    xmlns:tei="http://www.tei-c.org/ns/1.0"
    version="2.0">

    <xsl:output method="xml" encoding="utf-8" omit-xml-declaration="no" indent="yes"/>

    <xsl:template match="gutbook">
      <tei:TEI>
        <xsl:attribute name="xml:id">
        <xsl:value-of select="translate(translate(normalize-space(//titlepage/title/text()), ' ', '-'), '.', '')"/>
        <xsl:text>_</xsl:text>
        <xsl:value-of select="translate(translate(normalize-space(//titlepage/author/text()), ' ', '-'), '.', '')"/>
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

    <xsl:template match="pubinfo">
      
    </xsl:template>
    
    <xsl:template match="frontmatter/preface">
      <tei:titlePart type="preface">
        <xsl:apply-templates />
      </tei:titlePart>
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
        <!-- Is there a subhead? -->
        <xsl:if test="following-sibling::title">
          <xsl:text>: </xsl:text>
          <xsl:apply-templates select="following-sibling::title" mode="override"/>
        </xsl:if>
      </tei:head>
    </xsl:template>

    <xsl:template match="chapnum/title">
      <xsl:apply-templates />
    </xsl:template>

    <xsl:template match="title[not(preceding-sibling::chapnum)]|partnum">
      <tei:head><xsl:apply-templates /></tei:head>
    </xsl:template>

    <xsl:template match="subtitle" />

    <xsl:template match="subtitle" mode="subtitle">
      <tei:titlePart type="sub"><xsl:apply-templates /></tei:titlePart>
    </xsl:template>


    <xsl:template match="title[preceding-sibling::chapnum]" />
    <xsl:template match="title[preceding-sibling::chapnum]" mode="override">
      <xsl:apply-templates />
    </xsl:template>

    <xsl:template match="frontmatter/titlepage">
      <tei:titlePage>
	<xsl:apply-templates />
      </tei:titlePage>
    </xsl:template>
    <xsl:template match="frontmatter/titlepage/pubinfo">
      <tei:titlePart>
        <tei:note><xsl:apply-templates /></tei:note>
      </tei:titlePart>
    </xsl:template>

    <xsl:template match="bookbody/part/titlepage">
      <xsl:apply-templates />
    </xsl:template>


    <xsl:template match="titlepage/title">
      <tei:docTitle>
      <tei:titlePart><xsl:apply-templates /></tei:titlePart>
      <xsl:apply-templates select="../subtitle" mode="subtitle"/>
      </tei:docTitle>
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
    <xsl:template match="index" />

    <xsl:template match="frontmatter/preface/title">
      <tei:title>
        <xsl:apply-templates />
      </tei:title>
    </xsl:template>

    <xsl:template match="frontmatter/preface/para">
      <tei:note>
        <tei:p>
          <xsl:apply-templates />
        </tei:p>
      </tei:note>
    </xsl:template>

    <xsl:template match="chapsummary">
      <tei:head type="summary">
        <xsl:apply-templates />
      </tei:head>
    </xsl:template>

    <xsl:template match="epigraph">
      <tei:epigraph>
        <xsl:apply-templates />
      </tei:epigraph>
    </xsl:template>

    <xsl:template match="blockquote">
      <tei:q>
        <xsl:apply-templates />
      </tei:q>
    </xsl:template>

    <xsl:template match="attrib">
      <tei:bibl>
        <xsl:apply-templates />        
      </tei:bibl>
    </xsl:template>
    
    <xsl:template match="epigraph/para[place]">
      <tei:bibl>
        <tei:pubPlace><xsl:apply-templates />        </tei:pubPlace>
      </tei:bibl>
    </xsl:template>

    <xsl:template match="epigraph/para[date]">
      <tei:bibl>
        <tei:date><xsl:apply-templates />        </tei:date>
      </tei:bibl>
    </xsl:template>

    <xsl:template match="introduction">
      <tei:div type="preface">
        <xsl:apply-templates />
      </tei:div>
    </xsl:template>

    <xsl:template match="list">
      <tei:list>
        <xsl:apply-templates />
      </tei:list>
    </xsl:template>

    <xsl:template match="item">
      <tei:item>
        <xsl:apply-templates />
      </tei:item>
    </xsl:template>

    <!-- For Huck Finn -->
    <xsl:template match="htitlepage/place">
      <tei:div type="place"><tei:p><xsl:apply-templates /></tei:p></tei:div>
    </xsl:template>

    <xsl:template match="htitlepage/date">
      <tei:div type="date"><tei:p><xsl:apply-templates /></tei:p></tei:div>
    </xsl:template>

    
    <xsl:template match="poem">
      <tei:lg><xsl:apply-templates /></tei:lg>
    </xsl:template>

    <xsl:template match="line">
      <tei:l><xsl:apply-templates /></tei:l>
    </xsl:template>
    
    <xsl:template match="note">
      <tei:note><xsl:apply-templates /></tei:note>
    </xsl:template>

    <xsl:template match="footnote">
      <tei:note place="foot" type="footnote" resp="author" anchored="true">
        <xsl:attribute name="xml:id">
          <xsl:value-of select="@id" />
          <xsl:text>_</xsl:text>
          <xsl:value-of select="position()" />
        </xsl:attribute>
        <xsl:apply-templates />
      </tei:note>
    </xsl:template>

    <xsl:template match="reference[@ref]">
      <tei:anchor>
      <xsl:attribute name="xml:id">
        <xsl:value-of select="@ref" />
        <xsl:text>_</xsl:text>
        <xsl:value-of select="position()" />
      </xsl:attribute></tei:anchor>
    </xsl:template>

    <xsl:template match="reference[not(@ref)]">
    </xsl:template>
</xsl:stylesheet>

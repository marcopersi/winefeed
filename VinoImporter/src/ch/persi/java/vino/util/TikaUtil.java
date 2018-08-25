package ch.persi.java.vino.util;

import java.io.File;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.apache.tika.io.IOUtils;
import org.apache.tika.parser.ParsingReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

public class TikaUtil implements InputParser{

	private static final Logger log = LoggerFactory.getLogger(TikaUtil.class);
	private ParserSupport parserSupport = null;
	
	public void setParserSupport(ParserSupport theParserSupport)
	{
		parserSupport = theParserSupport;
	}

	public ParserSupport getParserSupport()
	{
		return parserSupport;
	}
	
	@Override
	public List<String> parse(String theFileName) {
		List<String> someLines = new ArrayList<>();
		File anInputFile = new File(theFileName);
		 Reader aReader = null;
		 try {
			 aReader = new ParsingReader(anInputFile);
			 String aText = IOUtils.toString(aReader);
			 String[] someStrings = parserSupport.compact(aText.split("\r\n"));
			 someLines = Arrays.asList(someStrings);
		 } catch (IOException e) {
			 log.error("Problem parsing the PDF", e);
		 } finally {
			 IOUtils.closeQuietly(aReader);
		 }
		 return someLines;
	}
	
}

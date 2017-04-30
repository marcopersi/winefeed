package ch.persi.java.vino.util;

import java.io.File;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.apache.tika.io.IOUtils;
import org.apache.tika.parser.ParsingReader;

public class TikaUtil extends AbstractParser{

	@Override
	public List<String> parse(String theFileName) {
		List<String> someLines = new ArrayList<>();
		File anInputFile = new File(theFileName);
		 Reader aReader = null;
		 try {
			 aReader = new ParsingReader(anInputFile);
			 String aText = IOUtils.toString(aReader);
			 String[] someStrings = compact(aText.split("\r\n"));
			 someLines = Arrays.asList(someStrings);
		 } catch (IOException e) {
			 e.printStackTrace();
		 } finally {
			 IOUtils.closeQuietly(aReader);
		 }
		 return someLines;
	}
	
}

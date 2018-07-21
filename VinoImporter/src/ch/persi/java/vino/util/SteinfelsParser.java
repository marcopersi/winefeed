package ch.persi.java.vino.util;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.apache.tika.metadata.PDF;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;

/**
 * an iText based {@link PDF} parser for all Steinfels files 
 * @author marcopersi
 *
 */
public class SteinfelsParser implements InputParser{

	private static final Logger log = LoggerFactory.getLogger(SteinfelsParser.class);
	private ParserSupport parserSupport = null;
	
	public void setParserSupport(ParserSupport theParserSupport)
	{
		parserSupport = theParserSupport;
	}

	public ParserSupport getParserSupport()
	{
		return parserSupport;
	}
	
	private List<String> extractLines(PdfReader thePDFReader) throws IOException {
		List<String> someLines = new ArrayList<>();
		for (int i=1;i<=thePDFReader.getNumberOfPages();i++)
		{
			// new line working for newer Steinfels format with price & lot at BEGINNING of line !
			String textFromPage = PdfTextExtractor.getTextFromPage(thePDFReader, i);
			someLines.addAll(Arrays.asList(parserSupport.compact(textFromPage.split("\n"))));
		}
		return someLines;
	}

	@Override
	public List<String> parse(String theFileName)  {
		List<String> someRecordLines = new ArrayList<>();
		PdfReader aPdfReader = null;
		try {
			aPdfReader = new PdfReader(theFileName);
			someRecordLines = extractLines(aPdfReader);
		} catch (Exception ex) {
			log.error(ex.getMessage());
		} finally {
			if (aPdfReader != null) {
				aPdfReader.close();
			}
		}
		return someRecordLines;
	}

}

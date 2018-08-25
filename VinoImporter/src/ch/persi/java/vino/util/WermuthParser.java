package ch.persi.java.vino.util;

import java.util.ArrayList;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;
import com.itextpdf.text.pdf.parser.SimpleTextExtractionStrategy;

/**
 * an iText based extractor for all Wermuth result files
 * @author marcopersi
 *
 */
public class WermuthParser implements InputParser{

	private static final Logger log = LoggerFactory.getLogger(SteinfelsParser.class);
	
	
	@Override
	public List<String> parse(String theFileName)  {
		List<String> someRecordLines = new ArrayList<>();
		PdfReader aPdfReader = null;
		try {
			aPdfReader = new PdfReader(theFileName);
			for (int i=1;i<=aPdfReader.getNumberOfPages();i++)
			{
				String textFromPage = PdfTextExtractor.getTextFromPage(aPdfReader, i, new SimpleTextExtractionStrategy());
				String[] split = textFromPage.split("\n");
				if (split != null &&split.length>1)
				{
					for (String string : split) {
						someRecordLines.add(string.trim());
					}
				}
			}
			
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

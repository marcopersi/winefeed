package ch.persi.java.vino.util;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;

public class iTextUtil extends AbstractParser {

	private static final Logger log = LoggerFactory.getLogger(iTextUtil.class);
	
	@Override
	public List<String> parse(String theFileName)  {
		List<String> someRecordLines = new ArrayList<>();
		PdfReader aPdfReader = null;
		try {
			aPdfReader = new PdfReader(theFileName);
			for (int i=1;i<=aPdfReader.getNumberOfPages();i++)
			{
				// original code, working for Wermuth & Co. 
//				String textFromPage = PdfTextExtractor.getTextFromPage(aPdfReader, i, new SimpleTextExtractionStrategy());

				
				// new line working for newer Steinfels format with price & lot at BEGINNING of line !
				String textFromPage = PdfTextExtractor.getTextFromPage(aPdfReader, i);
				someRecordLines.addAll(Arrays.asList(compact(textFromPage.split("\n"))));
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

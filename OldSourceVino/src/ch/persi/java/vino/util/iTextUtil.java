package ch.persi.java.vino.util;

import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;

public class iTextUtil {

	public static List<String> getLines(String theFileName) throws IOException{
		PdfReader aPdfReader = new PdfReader(theFileName);

		List<String> someRecordLines = new ArrayList<String>();
		
		for (int i=1;i<=aPdfReader.getNumberOfPages();i++)
		{
			String anExtractedText = PdfTextExtractor.getTextFromPage(aPdfReader, i);
			someRecordLines.addAll(Arrays.asList(anExtractedText.split("\n")));
		}
		return someRecordLines;
	}
}

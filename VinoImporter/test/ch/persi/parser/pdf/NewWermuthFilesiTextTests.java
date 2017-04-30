package ch.persi.parser.pdf;

import java.io.IOException;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;
import com.itextpdf.text.pdf.parser.SimpleTextExtractionStrategy;

public class NewWermuthFilesiTextTests {

	public static void main(String[] args) throws IOException {
		PdfReader aPDFReader = new PdfReader("test/resources/WZ-252_14032015_Resultate.pdf");
		
		try {
			
			for (int i = 1; i<= aPDFReader.getNumberOfPages();i++)
			{
				System.out.println(PdfTextExtractor.getTextFromPage(aPDFReader, i,new SimpleTextExtractionStrategy()));
			}
			System.out.flush();
		}
		catch(Exception e)
		{
			e.printStackTrace(System.out);
		}
		finally
		{
			aPDFReader.close();
		}
	}

}

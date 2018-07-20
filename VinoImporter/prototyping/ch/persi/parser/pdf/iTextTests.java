package ch.persi.parser.pdf;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;

public class iTextTests {

	/**
	 * @param args
	 * @throws IOException 
	 */
	public static void main(String[] args) throws IOException {
		PdfReader aPDFReader = new PdfReader("test/resources/379_05032016_Resultate.pdf");
		
		try (PrintWriter aPrintWriter = new PrintWriter(new FileOutputStream(new File("test/resources/target.txt")))) {
			for (int i=1;i<=aPDFReader.getNumberOfPages();i++)
			{
				aPrintWriter.println(PdfTextExtractor.getTextFromPage(aPDFReader, i));
			}
			aPrintWriter.flush();
			aPDFReader.close();
		}
	}

}

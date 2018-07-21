package ch.persi.parser.pdf;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.PrintWriter;

import org.apache.tika.metadata.PDF;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;
/**
 * Extracts just all the content from a {@link PDF} file using the iText library
 * Reason is that all of the different PDF libraries provide different results from text scanning
 * 
 * 
 * @author marcopersi
 *
 */
public class iTextTests {

	/**
	 * @param args
	 * @throws IOException 
	 */
	public static void main(String[] args) throws IOException {
		PdfReader aPDFReader = new PdfReader("prototyping/resources/WZ-255_14112015_Resultate.pdf");
		
		try (PrintWriter aPrintWriter = new PrintWriter(new FileOutputStream(new File("prototyping/resources/target.txt")))) {
			for (int i=1;i<=aPDFReader.getNumberOfPages();i++)
			{
				aPrintWriter.println(PdfTextExtractor.getTextFromPage(aPDFReader, i));
			}
			aPrintWriter.flush();
			aPDFReader.close();
		}
	}

}

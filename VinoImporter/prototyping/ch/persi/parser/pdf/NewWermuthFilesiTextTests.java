package ch.persi.parser.pdf;

import java.io.IOException;

import com.itextpdf.text.pdf.PdfReader;
import com.itextpdf.text.pdf.parser.PdfTextExtractor;
import com.itextpdf.text.pdf.parser.SimpleTextExtractionStrategy;

/**
 * parsing a specific result file from Wermuth, using iText as a library
 *
 * @author marcopersi
 */
public class NewWermuthFilesiTextTests {

    public static void main(String[] args) throws IOException {
        PdfReader aPDFReader = new PdfReader("prototyping/resources/WZ-259_19112016_Resultate");

        try {

            for (int i = 1; i <= aPDFReader.getNumberOfPages(); i++) {
                System.out.println(PdfTextExtractor.getTextFromPage(aPDFReader, i, new SimpleTextExtractionStrategy()));
            }
            System.out.flush();
        } catch (Exception e) {
            e.printStackTrace(System.out);
        } finally {
            aPDFReader.close();
        }
    }

}

package ch.persi.parser.pdf;

import java.io.File;
import java.io.IOException;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

/**
 * reading a @link PDF using the Apache PDFBox library
 *
 * @author marcopersi
 */
public class ApachePDFBoxTest {

    /**
     * @param args
     * @throws IOException
     */
    public static void main(String[] args) throws IOException {
        try (PDDocument pddDocument = PDDocument.load(new File("prototyping/resources/WZ-255_14112015_Resultate.pdf"));) {
            PDFTextStripper textStripper = new PDFTextStripper();
            textStripper.setAddMoreFormatting(true);
            String text = textStripper.getText(pddDocument);
            String[] split = text.split("\n");

            for (String string : split) {
                System.out.println("Line: '" + string + "'");
            }
        } catch (IOException ex) {
            ex.printStackTrace();
        }
    }

}

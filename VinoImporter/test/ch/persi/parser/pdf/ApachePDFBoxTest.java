package ch.persi.parser.pdf;

import java.io.File;
import java.io.IOException;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.util.PDFTextStripper;

public class ApachePDFBoxTest {

	/**
	 * @param args
	 * @throws IOException
	 */
	public static void main(String[] args) throws IOException {
		try (PDDocument pddDocument = PDDocument.load(new File("test/resources/379_05032016_Resultate.pdf"));) {
			PDFTextStripper textStripper = new PDFTextStripper();
			textStripper.setAddMoreFormatting(true);
			String text = textStripper.getText(pddDocument);
			String[] split = text.split("\r\n");

			for (String string : split) {
				System.out.println("Line: '" + string + "'");
			}
		} catch (IOException ex) {
			ex.printStackTrace();
		}
	}

}

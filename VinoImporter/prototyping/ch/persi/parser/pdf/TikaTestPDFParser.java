package ch.persi.parser.pdf;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;

import org.apache.tika.exception.TikaException;
import org.apache.tika.metadata.Metadata;
import org.apache.tika.parser.AutoDetectParser;
import org.apache.tika.parser.ParseContext;
import org.apache.tika.parser.Parser;
import org.apache.tika.sax.BodyContentHandler;
import org.xml.sax.ContentHandler;

/**
 * Parsing a PDF using the Tika library
 *
 * @author marcopersi
 */
public class TikaTestPDFParser {

    /**
     * @param args
     * @throws IOException
     * @throws TikaException
     */
    public static void main(String[] args) throws IOException, TikaException {
        test1();
    }

    private static final void test1() {
        try (BufferedInputStream is = new BufferedInputStream(new FileInputStream(new File("prototyping/resources/WZ-255_14112015_Resultate.pdf")))) {
            Parser parser = new AutoDetectParser();
            ContentHandler handler = new BodyContentHandler(System.out);
            Metadata metadata = new Metadata();
            parser.parse(is, handler, metadata, new ParseContext());
        } catch (Exception e) {
            e.printStackTrace(System.out);
        }
    }

}

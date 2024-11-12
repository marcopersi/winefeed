package ch.persi.java.vino.util;

import org.apache.pdfbox.pdmodel.PDDocument;
import org.apache.pdfbox.text.PDFTextStripper;

import java.io.File;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public class PDFBoxUtil implements InputParser {

    private static final int MINIMUM_CHARACTERS_PER_LINE = 10;

    private ParserSupport parserSupport = null;

    public ParserSupport getParserSupport() {
        return parserSupport;
    }

    public void setParserSupport(ParserSupport theParserSupport) {
        parserSupport = theParserSupport;
    }

    @Override
    public List<String> parse(String theFileName) {

        try (PDDocument pddDocument = PDDocument.load(new File(theFileName))) {
            List<String> someLines = new ArrayList<>();

            PDFTextStripper textStripper = new PDFTextStripper();
            textStripper.setAddMoreFormatting(true);
            String text = textStripper.getText(pddDocument);
            String[] someStrings = parserSupport.compact(text.split("\n"));
            if (someStrings != null && someStrings.length > 0) {
                for (String aLine : someStrings) {
                    if (aLine.length() > MINIMUM_CHARACTERS_PER_LINE) {
                        someLines.add(aLine);
                    }
                }
            }
            return someLines;
        } catch (IOException ex) {
            ex.printStackTrace();
        }
        return Collections.emptyList();
    }

}

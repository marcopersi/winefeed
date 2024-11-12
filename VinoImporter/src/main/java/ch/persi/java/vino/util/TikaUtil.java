package ch.persi.java.vino.util;

import org.apache.tika.parser.ParsingReader;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.File;
import java.io.IOException;
import java.io.Reader;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

public class TikaUtil implements InputParser {

    private static final Logger log = LoggerFactory.getLogger(TikaUtil.class);
    private ParserSupport parserSupport = null;

    public ParserSupport getParserSupport() {
        return parserSupport;
    }

    public void setParserSupport(ParserSupport theParserSupport) {
        parserSupport = theParserSupport;
    }

    @Override
    public List<String> parse(String theFileName) {
        List<String> someLines = new ArrayList<>();
        File anInputFile = new File(theFileName);

        try (Reader aReader = new ParsingReader(anInputFile)) {
            String aText = aReader.toString();
            String[] someStrings = parserSupport.compact(aText.split("\r\n"));
            someLines = Arrays.asList(someStrings);
        } catch (IOException e) {
            log.error("Serious problem parsing the PDF", e);
        }
        return someLines;
    }

}

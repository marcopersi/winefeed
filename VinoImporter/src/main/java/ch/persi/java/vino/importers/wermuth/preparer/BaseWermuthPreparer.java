package ch.persi.java.vino.importers.wermuth.preparer;

import java.io.File;
import java.io.FileNotFoundException;
import java.util.ArrayList;
import java.util.List;
import java.util.Scanner;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Base class for Wermuth preparers using Template Method pattern
 * Provides common logic for parsing Wermuth auction files
 */
public abstract class BaseWermuthPreparer {

    protected Pattern lotNumberPattern = Pattern.compile("^([0-9]{1,4}).*");
    protected int lastLotNumber = 1;

    /**
     * Template method - defines the algorithm structure
     */
    public void prepare() throws FileNotFoundException {
        File file = new File(getInputFilePath());
        List<String> lines = parseFile(file);
        
        for (String line : lines) {
            String cleaned = cleanLine(line);
            System.out.println(cleaned);
        }
    }

    /**
     * Parse file and merge lines that belong together
     */
    protected List<String> parseFile(File file) throws FileNotFoundException {
        List<String> lines = new ArrayList<>();

        try (Scanner input = new Scanner(file)) {
            while (input.hasNextLine()) {
                String nextLine = input.nextLine();
                Matcher matcher = lotNumberPattern.matcher(nextLine);

                if (matcher.matches() && isSequence(matcher.group(1), lastLotNumber)) {
                    lines.add(nextLine);
                    lastLotNumber++;
                } else {
                    // Merge with previous line
                    String previousLine = lines.get(lines.size() - 1).replaceAll("[\\r\\n]+", "");
                    String mergedLine = previousLine + " " + nextLine + " ";
                    lines.remove(lines.size() - 1);
                    lines.add(mergedLine);
                }
            }
        }

        return lines;
    }

    /**
     * Check if lot number is in sequence
     */
    protected boolean isSequence(String lotNumberAsString, int last) {
        try {
            int lotNumber = Integer.parseInt(lotNumberAsString);
            return lotNumber == last;
        } catch (NumberFormatException e) {
            return false;
        }
    }

    /**
     * Clean line by removing unwanted characters and regions
     * Hook method - can be overridden by subclasses
     */
    protected String cleanLine(String line) {
        return line
                .replaceAll("[\\u201C\\u201D\\u00AB\\u00BB\\u2018\\u201C\\u201E]", "")
                .replaceAll("\\s{2}", " ")
                .replaceAll("CHF", " ")
                .replace(".00", " ")
                .replace("AC/MC, ", "")
                .replace("MO, ", "")
                .replace("AC/MO, ", "")
                .replace("MO/IGT, ", "")
                .replace("MO/DOC", "")
                .replace("MO/DOCG,", "")
                .replace("AC/", "")
                .replace("AC/IGT, ", " ")
                .replace("MO/DO, ", " ")
                .replace("Côte de Nuits, ", " ")
                .replace("Margaux,", " ")
                .replace("Pauillac, ", "")
                .replace("St. Julien, ", " ")
                .replace("St. Emilion, ", " ")
                .replace("Pomerol, ", " ")
                .replace("Napa Valley, ", " ")
                .replace("St. Cruz Mountain, ", "")
                .replace("St. Estèphe, ", "")
                .replaceAll("Pé|essac.*Lé|eognan, ", " ")
                .replace("Sauternes, ", "")
                .replace("Burgenland, ", " ")
                .replace("Languedoc, ", " ")
                .replaceAll("\\(.*\\)", " ")
                .replace("Calonge, ", " ")
                .replace("Barsac, ", " ")
                .replace("Barsac- Sauternes, ", " ")
                .replace("Côte de Beaune, ", " ")
                .replace("Toscana, ", " ")
                .replace("Haut-Médoc, ", " ")
                .replace("PessacsLéognan", " ")
                .replace("Moulis-Médoc, ", " ")
                .replace("Douro, ", "")
                .replace("Limoux, ", "")
                .replace("crusbourgeois exceptionnels", " ")
                .replace("crus bourgeois exceptionnel", " ")
                .trim();
    }

    /**
     * Abstract method - must be implemented by subclasses
     * @return path to input file
     */
    protected abstract String getInputFilePath();
}

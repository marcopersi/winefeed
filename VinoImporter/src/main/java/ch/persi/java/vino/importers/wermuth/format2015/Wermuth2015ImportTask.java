package ch.persi.java.vino.importers.wermuth.format2015;

import ch.persi.java.vino.domain.*;
import ch.persi.java.vino.importers.AbstractImportTask;
import ch.persi.java.vino.importers.DateParsingStrategy;
import ch.persi.java.vino.importers.Tuple2;
import lombok.val;
import org.apache.commons.lang3.ArrayUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.math.BigDecimal;
import java.util.List;
import java.util.Objects;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

import static ch.persi.java.vino.domain.VinoConstants.*;
import static java.lang.Integer.parseInt;
import static org.apache.commons.lang3.math.NumberUtils.isCreatable;

/**
 * The import task which cares about the Wermuth/Denz files which have changed since 2015.
 * Starting with first auction in 2015, Wermuth/Denz Weine provides the required info in one result file in the format PDF.
 * So there is no need to search a catalog, match the found lots with a result file and get the realized "hammer" prize then.
 *
 * @author marcopersi
 */
public class Wermuth2015ImportTask extends AbstractImportTask {

    public static final Pattern aRecordLinePattern = Pattern.compile("^([0-9]{1,4})\\s(.*)\\s([0-9]{1,3})\\s(.*[fF]lasche.*|Doppelmagnum.*),?\\s([0-9]{4}),?.*(pro[a-zA-Z\\.\\s]*\\s)([0-9]{2,5}.*$)");
    private static final Logger log = LoggerFactory.getLogger(Wermuth2015ImportTask.class);
    private String importDirectory = null;

    /**
     * only public for testing purposes
     *
     * @return a cleaned String
     */
    public static String clean(String theLine) {
        return theLine.replaceAll("1er", "").replace("G|grand cru,", "").replaceAll("2ème|3ème|4ème|5ème", "").replaceAll("cru burgoise", "").replaceAll("1 cru ", "")
                .replaceAll("1 er|cru", "").replaceAll("Total ", "").replaceAll("«|»|“|”|„", "").replaceAll("CHF ", "").replaceAll("SFr.", "").replaceAll("Fr.", "")
                .replace(".00", "").replaceAll("\\(.*\\)", "").replaceAll("\\s{2,}", SPACE).replaceAll("Cru|cru", "");
    }

    public static int processNoOfBottles(String theNoOfBottles, String theLotOrDozenIndicator) {
        int aNoOfUnits = parseInt(theNoOfBottles);

        if (theLotOrDozenIndicator.contains("pro Dutzend") || theLotOrDozenIndicator.contains("pro Dz")) {
            aNoOfUnits *= 12;
        }

        return aNoOfUnits;
    }

    public static LotPriceInfo processLotPricing(String theInput) {
        //the last part drops any characters, actually there should be only digits and probably a dash (-) character, but nothing else anymore.
        String aCleanedInputLine = theInput.replaceAll("[a-zA-Z\\.']", "");
        Pattern aPricePattern = Pattern.compile("^(\\d{1,5})-(\\d{1,5})\\s?{1,}([0-9\\-]{1,5})?\\s?$");

        Matcher matcher = aPricePattern.matcher(aCleanedInputLine);
        if (!matcher.matches()) {
            throw new IllegalStateException("Price info did not look as expected!: " + aCleanedInputLine);
        }

        int aLowerPrice = parseInt(matcher.group(1));
        int anUpperPrice = parseInt(matcher.group(2));
        int aRealizedPrice = isCreatable(matcher.group(3)) ? parseInt(matcher.group(3)) : 0;
        return new LotPriceInfo(aLowerPrice, anUpperPrice, aRealizedPrice);
    }

    private static Tuple2<Boolean, String> processOWC(String theLine) {

        boolean isOHK = false;
        if (theLine.contains(OHK) || theLine.contains(OC)) {
            isOHK = true;
        }

        return new Tuple2<>(isOHK, theLine.replace(OHK, "").replace(", " + OC, ""));
    }

    public static Tuple2<String, String> processOrigin(String theLine) {

        for (Origin o : Origin.values()) {
            String anOriginIdentifier = o.getOriginIdentifier();
            if (theLine.contains(anOriginIdentifier)) {
                StringBuilder aRegex = new StringBuilder();
                aRegex.append("^.*( ").append(anOriginIdentifier).append(", [a-zA-Zäüöôèéâ\\. ]*),.*");
                Pattern aPattern = Pattern.compile(aRegex.toString(), Pattern.CASE_INSENSITIVE);
                Matcher matcher = aPattern.matcher(theLine.trim());
                if (matcher.matches()) {
                    String anOriginString = matcher.group(1);
                    String anOrigin = anOriginString.replace(",", "").trim();
                    return new Tuple2<>(anOrigin, theLine.replace(anOriginString, ""));
                }

            }
        }
        return new Tuple2<>(null, theLine);

    }

    @Override
    public void saveWineOfferings(List<String> theLines) throws IOException {

        if (theLines.isEmpty()) {
            throw new IllegalStateException("Received no lines from parser, something's terribly wrong !");
        }

        int aProcessLineIndex = 0;
        for (String aLine : theLines) {
            // cleaning
            log.debug("Working on line: {}", aLine);
            String aCleanedLine = clean(aLine);

            // processing
            WineOffering aWineOffering = processLine(aCleanedLine);


			/* Notiz: diese Zeilen sind auskommentiert / zu auskommentieren, weil ich nach dem Lesen der Files zuerst zur Vorbereitung
			alles in eine Textdatei lese. Diese kann man mit Visual Studio Code schnell optimieren
			das Resultat dieser Optimierung ist eine INput - Resultate Datei die nahezu 100% Verarbeitung gehen sollte. */

            // writing results

            if (aWineOffering != null) {
                anOutputWriter.write(aWineOffering.toXLSString());
                anOutputWriter.flush();
            } else {
                aSkippedRowsWriter.write(aCleanedLine + "\n");
                aSkippedRowsWriter.flush();
            }
            aProcessLineIndex++;
        }
        log.info("Processed: {} out of:{} lines ! ", aProcessLineIndex, theLines.size());
    }

    public final WineOffering processLine(String theWineRecordLine) {

        Tuple2<Boolean, String> anOWCProcess = processOWC(theWineRecordLine);
        String aWineRecordLineWithoutOWC = anOWCProcess.getValue();

        Tuple2<String, String> anOriginProcess = processOrigin(aWineRecordLineWithoutOWC);
        String anOrigin = anOriginProcess.getKey();
        String aWineRecordLineWithoutOWCOrigin = anOriginProcess.getValue();

        Matcher aRecordLineMatcher = aRecordLinePattern.matcher(aWineRecordLineWithoutOWCOrigin);

        if (aRecordLineMatcher.matches()) {
            Offering anOffering = new Offering();
            anOffering.setProvider(Provider.WERMUTH.getProviderCode());
            anOffering.setOfferingDate(getAuctionDate());

            String aLotNumber = aRecordLineMatcher.group(1);
            anOffering.setProviderOfferingId(aLotNumber);

            anOffering.setIsOHK(anOWCProcess.getKey());
            anOffering.setEventIdentifier(getEventIdentifier());

            String aLinePart = aRecordLineMatcher.group(6);
            int aNoOfBottles = processNoOfBottles(aRecordLineMatcher.group(3), aLinePart);
            anOffering.setNoOfBottles(aNoOfBottles);

            LotPriceInfo processLotPricing = processLotPricing(aRecordLineMatcher.group(7));
            anOffering.setPriceMax(processLotPricing.getUpperPrice());
            anOffering.setPriceMin(processLotPricing.getLowerPrice());
            anOffering.setRealizedPrice(processLotPricing.getRealizedPrice());

            Wine aWine = new Wine();
            String aWineName = aRecordLineMatcher.group(2);
            if (aWineName.contains(",")) {
                String[] split = aWineName.split(",");

                // processing origin
                if (!ArrayUtils.isEmpty(split)) {
                    String aPossibleWineName = split[0].trim();
                    if (split.length == 2) {
                        aWine.setProducer(split[1].trim());
                    }
                    aWineName = aPossibleWineName;
                }
            }

            aWine.setOrigin(anOrigin);
            aWine.setName(aWineName);

            String group = aRecordLineMatcher.group(5);
            int vintage = parseInt(group);
            aWine.setVintage(vintage);

            Unit aWineUnit = processBottleSize(aRecordLineMatcher.group(4));
            return new WineOffering(aWine, aWineUnit, anOffering);
        }
        return null;
    }

    @Override
    public String getImportDirectory() {
        return importDirectory;
    }

    public void setImportDirectory(String theImportDirectory) {
        importDirectory = theImportDirectory;
    }

    @Override
    public void execute() {
        // checking for to be imported files at fileSystem.
        val anImportDirectory = checkFiles();
        if (anImportDirectory == null) return;

        for (String aFileName : Objects.requireNonNull(anImportDirectory.list())) {
            String[] someFileNameParts = aFileName.split("_");
            if (!aFileName.startsWith(".") && aFileName.contains("Resultate") && someFileNameParts.length >= 3) {
                try {
                    log.info("Start import of file: {}", aFileName);
                    String anImportFile = getImportDirectory() + aFileName;
                    List<String> someLines = parser.parse(anImportFile);
                    log.info("Received '{}' lines out of the PDF file !", someLines.size());
                    setAuctionDate(new DateParsingStrategy(someFileNameParts[1]).getAuctionDate());

                    Matcher compile = Pattern.compile("(WZ\\-//d{1,4}).*").matcher(aFileName);
                    if (compile.matches()) {
                        setEventIdentifier(compile.group(1));
                    }

                    // PDFs are nasty, some have the tag of the auction (252 or 287..)in front of every single line. cleaning this.
//					someLines = ResultFilebasedLotLinePreparer.prepare(someLines);

                    importFile(someLines, Provider.WERMUTH);
                } catch (Exception anException) {
                    log.error("Executing Wermuth Import Task has a serious problem with file {}!, got exception {}", aFileName, anException);
                }
                log.info("Import of file {} successfully done", aFileName);
            }
        }
    }

    public final Unit processBottleSize(String theBottleSizeIndicator) {
        BigDecimal aSize = determineSize(theBottleSizeIndicator);
        return new Unit(aSize);
    }

}
